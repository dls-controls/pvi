from pathlib import Path
from typing import Dict, Iterator, List, Union

from pydantic import BaseModel, Field
from ruamel.yaml import YAML

from ._aps import APSFormatter
from ._asyn import AsynFloat64, AsynProducer, AsynString
from ._dls import DLSFormatter
from ._macros import FloatMacro, IntMacro, StringMacro
from ._types import Component, File, Group

# from ._stream import StreamFloat64, StreamString, StreamProducer

MacroUnion = Union[FloatMacro, StringMacro, IntMacro]
ProducerUnion = Union[AsynProducer]  # , StreamProducer, SoftProducer]
FormatterUnion = Union[APSFormatter, DLSFormatter]
ComponentUnion = Union["ComponentGroup", AsynFloat64, AsynString]


class ComponentGroup(Group[Component]):
    """Group that can contain multiple parameters or other Groups."""

    children: List[ComponentUnion] = Field(
        ..., description="Child Parameters or Groups"
    )


ComponentGroup.update_forward_refs()


def walk_dicts(tree: List[Dict]) -> Iterator[Dict]:
    """Depth first traversal of tree"""
    for t in tree:
        assert isinstance(t, dict), f"Expected dict, got {t}"
        yield t
        yield from walk_dicts(t.get("children", []))


class Schema(BaseModel):
    description: str = Field(..., description="Description of what this Device does")
    macros: List[MacroUnion] = Field(
        [], description="Macros needed to make an instance of this"
    )
    template: str = Field(
        ..., description="Template file that should be loaded by the IOC"
    )
    startup: str = Field(
        "", description="Lines to insert into the startup script of IOC"
    )
    screens: List[File] = Field([], description="List of paths to associated screens")
    includes: List[File] = Field(
        [], description="YAML files to include in the definitions"
    )
    local: str = Field(
        None, description="YAML file that overrides this for local changes"
    )
    producer: ProducerUnion = Field(
        ..., description="The Producer class to make Records and the Device"
    )
    formatter: FormatterUnion = Field(
        ..., description="The Formatter class to format the output"
    )
    components: List[ComponentUnion] = Field(
        ..., description="The Components to pass to the Producer"
    )

    @classmethod
    def load(cls, path: Path, basename: str) -> "Schema":
        data = YAML().load(path / f"{basename}.pvi.yaml")
        local = data.get("local", None)
        if local:
            local_path = path / local.replace("$(basename)", basename)
            overrides = YAML().load(local_path)
            for k, v in overrides.items():
                if k == "components":
                    # Merge
                    by_name = {}
                    for existing in walk_dicts(data["components"]):
                        by_name[existing["name"]] = existing
                    for component in v:
                        by_name[component["name"]].update(component)
                else:
                    # Replace
                    data[k] = v
        schema = cls(**data)
        return schema


Schema.update_forward_refs()
