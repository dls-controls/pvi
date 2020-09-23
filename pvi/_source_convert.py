import os
import re
from typing import Any, Dict, List, Tuple
from pathlib import Path

from pydantic import BaseModel, Field, FilePath

from ._schema import Schema, ComponentUnion
from ._util import get_param_set


class Source:

    def __init__(self, cpp: FilePath, h: FilePath):
        self.cpp = cpp
        self.h = h


class SourceConverter(BaseModel):
    cpp: FilePath = Field(..., description="cpp file to convert to yaml")
    h: FilePath = Field(..., description="header file to convert to yaml")
    module_root: Path = Field(..., description="Path to root of module")
    parameter_infos: List[str]

    def __init__(self, **data: Any):
        super().__init__(**data)

        with open(self.cpp) as f:
            cpp = f.read()
        with open(self.h) as f:
            h = f.read()
        object.__setattr__(self, "source", Source(cpp, h))

        device_class, parent_class = self._extract_device_and_parent_class()
        object.__setattr__(self, "device_class", device_class)
        object.__setattr__(self, "parent_class", parent_class)
        object.__setattr__(
            self, "define_strings", self._extract_define_strs(self.parameter_infos)
        )

        object.__setattr__(
            self, "string_info_map", self._get_string_info_map(self.define_strings)
        )
        object.__setattr__(
            self,
            "create_param_strings",
            self._extract_create_param_strs(self.string_info_map.keys()),
        )

        object.__setattr__(
            self,
            "string_index_map",
            self._get_string_index_map(self.create_param_strings),
        )
        object.__setattr__(
            self,
            "declaration_strings",
            self._extract_index_declarations(self.string_index_map.values()),
        )

    def _extract_device_and_parent_class(self) -> str:
        # e.g. extract 'NDPluginDriver' and 'asynNDArrayDriver' from
        # class epicsShareClass NDPluginDriver : public asynNDArrayDriver, public epicsThreadRunable {
        class_extractor = re.compile(r"class.* (\w+) : \w+ (\w+) (?:, .*)?{")
        classes = re.search(class_extractor, self.source.h).groups()

        return classes

    def _extract_define_strs(self, info_strings: List[str]) -> List[str]:
        # e.g. extract: #define SimGainXString                "SIM_GAIN_X";
        define_extractor = re.compile(r'\#define[_A-Za-z0-9 ]*"[^"]*".*')
        definitions = re.findall(define_extractor, self.source.h)
        # We only want to extract the defines for the given parameter infos
        definitions = filter_strings(definitions, info_strings)
        return definitions

    def _extract_create_param_strs(self, param_strings: List[str]) -> List[str]:
        # e.g. extract: createParam(SimGainXString, asynParamFloat64, &SimGainX);
        create_param_extractor = re.compile(r"createParam\([^\)]*\);.*")
        create_param_strs = re.findall(create_param_extractor, self.source.cpp)
        # We only want to extract the createParam calls for the given parameter strings
        create_param_strs = filter_strings(create_param_strs, param_strings)
        return create_param_strs

    def _extract_index_declarations(self, index_names: List[str]) -> List[str]:
        # e.g. extract:     int SimGainX;
        declaration_extractor = re.compile(r"\s*int [^;]*;")
        declarations = re.findall(declaration_extractor, self.source.h)
        # We only want to extract the declarations for the given index names
        # This also filters any generic int parameter definitions in the class and some comments
        declarations = filter_strings(declarations, index_names)
        return declarations

    def _get_string_info_map(self, define_strings: List[str]) -> Dict[str, str]:
        string_info_map = dict(
            self._parse_definition_str(definition) for definition in define_strings
        )
        return string_info_map

    @staticmethod
    def _parse_definition_str(definition_str: str) -> Tuple[str, str]:
        # e.g. from: #define SimGainXString                "SIM_GAIN_X";
        # extract:
        # Group1: SimGainXString
        # Group2: SIM_GAIN_X
        define_extractor = re.compile(r'(?:\#define) ([A-Za-z0-9]*) *"([^"]*)')
        string_info_pair = re.findall(define_extractor, definition_str)[0]
        return string_info_pair

    def _get_string_index_map(self, create_param_strings: List[str]) -> Dict[str, str]:
        string_index_dict = dict(
            [
                self._parse_create_param_str(create_param_str)
                for create_param_str in create_param_strings
            ]
        )
        return string_index_dict

    @staticmethod
    def _parse_create_param_str(create_param_str: str) -> Tuple[str, str]:
        # e.g. from: createParam(SimGainXString, asynParamFloat64, &SimGainX);
        # extract: SimGainXString,               asynParamFloat64, &SimGainX
        create_param_extractor = re.compile(r"(?:createParam\()([^\)]*)(?:\))")
        # There are two signatures for createParam. 3 argument and 4 argument
        # I think we are only ever interested in the final three arguments
        create_param_args = (
            re.findall(create_param_extractor, create_param_str)[0]
            .replace(" ", "")
            .split(",")[-3:]
        )
        string_index_pair = (create_param_args[0], create_param_args[2].strip("&"))
        return string_index_pair

    def _get_index_info_map(self) -> Dict[str, str]:
        index_string_map = dict(
            (index, string) for string, index in self.string_index_map.items()
        )
        index_info_map = dict(
            (index, self.string_info_map[string])
            for index, string in index_string_map.items()
        )
        return index_info_map

    def get_top_level_text(self) -> str:
        extracted_cpp = self._convert_cpp(self.source.cpp)
        extracted_h = self._convert_h(self.source.h)

        return Source(extracted_cpp, extracted_h)

    def _convert_cpp(self, original_cpp_text: str) -> str:
        unwanted_strings = self.create_param_strings

        # Re-create text with unwanted lines ommited
        lines = original_cpp_text.splitlines()
        lines = [
            line
            for line in lines
            if line.lstrip()
            not in [unwanted_string.lstrip() for unwanted_string in unwanted_strings]
        ]
        cpp_text = "\n".join(lines)

        # Insert accessors for parameters that have been moved to the param set
        parameters = list(self.string_index_map.values())
        parent_components = find_parent_components(self.parent_class, self.module_root,)
        parameters += [
            parameter.index_name
            for component in parent_components
            for parameter in component.children
        ]
        cpp_text = self._insert_param_set_accessors(cpp_text, parameters)

        # Add the constructor param set parameter
        cpp_text = cpp_text.replace(
            f"::{self.device_class}(",
            f"::{self.device_class}({self.device_class}ParamSet* paramSet, ",
        )

        # Add the initialiser list base class param set parameter
        parent_param_set = get_param_set(self.parent_class)
        cpp_text = cpp_text.replace(
            f"{self.parent_class}(",
            f"{self.parent_class}(static_cast<{parent_param_set}*>(paramSet), ",
        )

        # Add the param set to the initialiser list
        cpp_text = re.sub(
            # Driver constructor and initialiser list, all whitespace between ) and {
            r"(::" + self.device_class + r"\([^{]+\))(\s*){",
            # Insert param set after last entry in initialiser list, in between match groups 1 and 2
            r"\1,\n    paramSet(paramSet)\2{",
            cpp_text,
        )

        return cpp_text

    def _convert_h(self, original_h: str) -> str:
        unwanted_strings = [
            string.strip() for string in self.define_strings + self.declaration_strings
        ]

        # Remove FIRST_*_PARAM define
        first_param_extractor = re.compile(r"")
        first_param_string = re.search(first_param_extractor, original_h).group()
        unwanted_strings += first_param_string

        # Re-create text with unwanted lines ommited
        lines = original_h.splitlines()
        lines = [line for line in lines if line.strip() not in unwanted_strings]
        h_text = "\n".join(lines)

        # Add the constructor param set parameter
        h_text = h_text.replace(
            f" {self.device_class}(",
            f" {self.device_class}({self.device_class}ParamSet* paramSet, ",
        )

        # Add the include
        idx = h_text.index(f'#include "{self.parent_class}.h"')
        h_text = (
            h_text[:idx] + f'#include "{self.device_class}ParamSet.h"\n' + h_text[idx:]
        )
        # Add the param set pointer member definition
        protected_extractor = re.compile(r".*protected:")
        protected_str = re.findall(protected_extractor, h_text)[0]
        param_set_definition = f"    {self.device_class}ParamSet* paramSet;"
        h_text = h_text.replace(
            protected_str, protected_str + "\n" + param_set_definition
        )

        # Replace FIRST_*_PARAM definition
        h_text = re.sub(
            r"(#define FIRST_\w+_PARAM) \w+",
            r"\1 paramSet->FIRST_" + self.device_class.upper() + "PARAMSET_PARAM",
            h_text,
        )

        return h_text

    @staticmethod
    def _insert_param_set_accessors(text: str, parameters: List[str]) -> str:
        for parameter in parameters:
            # Only match parameter name exactly, not others with same prefix
            text = re.sub(
                r"(\W)" + parameter + r"(\W)", r"\1paramSet->" + parameter + r"\2", text
            )
        return text


def find_parent_components(yaml_name: str, module_root: str) -> List[ComponentUnion]:
    if yaml_name == "asynPortDriver":
        return []  # asynPortDriver is the most base class and has no parameters

    # Look in this module first
    if f"{yaml_name}.pvi.yaml" in os.listdir(os.path.join(module_root, "pvi")):
        directory = os.path.join(module_root, "pvi")
    else:
        # TODO: Search configure/RELEASE paths
        raise IOError(f"Cannot find {yaml_name}.pvi.yaml")

    schema = Schema.load(Path(directory), Path(yaml_name))

    return schema.components + find_parent_components(schema.parent, module_root)


def filter_strings(strings: List[str], filters: List[str]) -> List[str]:
    return [
        string for string in strings if any(filter_ in string for filter_ in filters)
    ]
