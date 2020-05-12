"""The types that should be inherited from or produced by Fields."""

from typing import Any, Callable, Dict, List, Type, TypeVar, Union

from pydantic import BaseModel, Field

from .another_repo import ChannelConfig, DeviceConfig, Group, Tree, WithLabel, WithType


# These classes allow us to generate Records, Devices and Channels in intermediate files
class Record(BaseModel):
    name: str = Field(..., description="The name of the record e.g. $(P)$(M)Status")
    type: str = Field(..., description="The record type string e.g. ao, stringin")
    fields_: Dict[str, str] = Field(
        ..., description="The record fields", alias="fields"
    )
    infos: Dict[str, str] = Field({}, description="Any infos to be added to the record")


class AsynParameter(BaseModel):
    name: str = Field(..., description="Asyn parameter name")
    type: str = Field(..., description="Asyn parameter type")
    description: str = Field(..., description="Comment about this parameter")


# These are used in the definition of the Schema


C = TypeVar("C", bound="Component")
S = TypeVar("S")


class Component(WithLabel):
    """Something that can appear in the tree of components to make up the
    device."""

    @classmethod
    def on_each_node(
        cls: Type[C], tree: Tree["Component"], func: Callable[[C], List[S]]
    ) -> Tree[S]:
        """Visit each node of the tree of type typ, calling func on each leaf"""
        out: List[Union[S, Group[S]]] = []
        for t in tree:
            if isinstance(t, Group):
                group: Group[S] = Group(
                    name=t.name,
                    label=t.label,
                    children=cls.on_each_node(t.children, func),
                )
                out.append(group)
            elif isinstance(t, cls):
                out += func(t)
        return out


class File(BaseModel):
    path: str = Field(..., description="Path to the file, can include macros")
    macros: Dict[str, Any] = Field(
        {}, description="Extra macros to pass along with the macros from this file"
    )


class Producer(WithType):
    def produce_records(self, components: Tree[Component]) -> Tree[Record]:
        """Produce a Record tree structure for database template

        Args:
            components: Tree without base class Component instances

        Returns:
            Record tree structure that should be passed to the Formatter
        """
        raise NotImplementedError(self)

    def produce_asyn_parameters(
        self, components: Tree[Component]
    ) -> Tree[AsynParameter]:
        """Produce any files that need to go in the src/ directory

        Args:
            components: Tree without base class Component instances

        Returns:
            AsynParameter tree structure that should be passed to the Formatter
        """
        raise NotImplementedError(self)

    def produce_channels(self, components: Tree[Component]) -> Tree[ChannelConfig]:
        """Produce a channel tree structure for making screens

        Args:
            components: Tree including base class Component instances

        Returns:
            Channel tree structure that should be passed to the Formatter
        """
        raise NotImplementedError(self)


class Formatter(WithType):
    def format_adl(self, device: DeviceConfig, basename: str) -> str:
        raise NotImplementedError(self)

    def format_edl(self, device: DeviceConfig, basename: str) -> str:
        raise NotImplementedError(self)

    def format_opi(self, device: DeviceConfig, basename: str) -> str:
        raise NotImplementedError(self)

    def format_bob(self, device: DeviceConfig, basename: str) -> str:
        raise NotImplementedError(self)

    def format_ui(self, device: DeviceConfig, basename: str) -> str:
        raise NotImplementedError(self)

    def format_yaml(self, device: DeviceConfig, basename: str) -> str:
        raise NotImplementedError(self)

    def format_csv(self, device: DeviceConfig, basename: str) -> str:
        raise NotImplementedError(self)

    def format_template(self, records: Tree[Record], basename: str) -> str:
        raise NotImplementedError(self)

    def format_h(self, parameters: Tree[AsynParameter], basename: str) -> str:
        raise NotImplementedError(self)

    def format_cpp(self, parameters: Tree[AsynParameter], basename: str) -> str:
        raise NotImplementedError(self)
