import re
from enum import Enum
from typing import Any, Dict, Generic, Iterator, List, Sequence, TypeVar, Union

from pydantic import BaseModel, Field


def camel_to_title(name):
    """Takes a CamelCaseFieldName and returns an Title Case Field Name
    Args:
        name (str): E.g. CamelCaseFieldName
    Returns:
        str: Title Case converted name. E.g. Camel Case Field Name
    """
    split = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z0-9]|$)", name)
    ret = " ".join(split)
    ret = ret[0].upper() + ret[1:]
    return ret


# These must match the types defined in coniql schema
class DisplayForm(str, Enum):
    """Instructions for how a number should be formatted for display."""

    DEFAULT = "Default"
    STRING = "String"
    BINARY = "Binary"
    DECIMAL = "Decimal"
    HEX = "Hexadecimal"
    EXPONENTIAL = "Exponential"
    ENGINEERING = "Engineering"


class Widget(str, Enum):
    """Widget that should be used to display this Channel"""

    #: Editable text input
    TEXTINPUT = "Text Input"
    #: Read-only text display
    TEXTUPDATE = "Text Update"
    #: Multiline read-only text display
    MULTILINETEXTUPDATE = "Multiline Text Update"
    #: Read-only LED indicator
    LED = "LED"
    #: Editable combo-box style menu for selecting between fixed choices
    COMBO = "Combo"
    #: Editable check box
    CHECKBOX = "Checkbox"
    #: Editable progress type bar
    BAR = "Bar"
    #: Clickable button to send default value to Channel
    BUTTON = "Button"
    #: X-axis for lines on a graph. Only valid within a Group with widget Plot
    PLOTX = "Plot X"
    #: Y-axis for a line on a graph. Only valid within a Group with widget Plot
    PLOTY = "Plot Y"


class Layout(str, Enum):
    """Widget that should be used to display this Group"""

    #: Screen with children in it
    SCREEN = "Screen"
    #: Group box with children vertically within it
    BOX = "Box"
    #: Graph canvas with each Plot Y as a line in it against Plot X
    PLOT = "Plot"
    #: A single row of a table, containing Channels that aren't arrays
    ROW = "Row"
    #: Table of Rows with same named fields, or columns of array Channels
    TABLE = "Table"


class WithTypeMetaClass(type(BaseModel)):  # type: ignore
    def __new__(mcs, name, bases, namespace, **kwargs):
        # Override type in namespace to be the literal value of the class name
        namespace["type"] = Field(name, const=True)
        return super().__new__(mcs, name, bases, namespace, **kwargs)


class WithType(BaseModel, metaclass=WithTypeMetaClass):
    """BaseModel that adds a type parameter from class name."""

    type: str


class WithLabel(WithType):
    name: str = Field(
        ...,
        description="CamelCase name to uniquely identify this within its parent",
        regex=r"([A-Z][a-z0-9]*)*$",
    )
    label: str = Field(
        None,
        description="The GUI Label for this, default is name converted to Title Case",
    )

    def get_label(self) -> str:
        """If the component has a label, use that, otherwise
        return the Title Case version of its camelCase name"""
        label = self.label
        if label is None:
            label = camel_to_title(self.name)
        return label


T = TypeVar("T")
Tree = Sequence[Union[T, "Group[T]"]]


class Group(WithLabel, Generic[T]):
    """Group that can contain multiple parameters or other Groups."""

    children: Tree[T]
    layout: Layout = Field(
        Layout.BOX, description="The layout to arrange the children within"
    )


def walk(tree: Tree[T]) -> Iterator[Union[T, Group[T]]]:
    """Depth first traversal of tree"""
    for t in tree:
        yield t
        if isinstance(t, Group):
            yield from walk(t.children)


class Macro(WithType):
    name: str = Field(
        ..., description="The name of the Macro that will be passed when instantiated"
    )
    description: str = Field(
        ..., description="Description of what the Macro will be used for"
    )
    value: Any


VALUE_FIELD = Field(
    None, description="The default value of the parameter, None means required"
)


class StringMacro(Macro):
    value: str = VALUE_FIELD


class FloatMacro(Macro):
    value: float = VALUE_FIELD


class IntMacro(Macro):
    value: int = VALUE_FIELD


MacroUnion = Union[FloatMacro, StringMacro, IntMacro]


class ChannelConfig(WithLabel):
    read_pv: str = Field(
        None, description="The pv to get from, None means not readable (an action)"
    )
    write_pv: str = Field(
        None, description="The pv to put to, None means not writeable (a readback)"
    )
    # The following are None to allow multiple references to channels
    widget: Widget = Field(None, description="Which widget to use for the Channel")
    description: str = Field(None, description="Description of what the Channel does")
    display_form: DisplayForm = Field(
        None, description="How should numeric values be displayed"
    )


class ChildDeviceConfig(WithLabel):
    file: str = Field(
        ..., description="Filename with extension coniql.yaml containing Device config"
    )
    macros: Dict[str, Any] = Field(
        {}, description="Macro substitutions to make while instantiating Device config"
    )


ConfigUnion = Union["ChannelConfigGroup", ChannelConfig, ChildDeviceConfig]


class ChannelConfigGroup(Group[ConfigUnion]):
    """Group that can contain multiple parameters or other Groups."""

    children: List[ConfigUnion] = Field(
        ..., description="Child configs for Channels, Devices or Groups"
    )


ChannelConfigGroup.update_forward_refs()


class DeviceConfig(BaseModel):
    macros: List[MacroUnion] = Field(
        [], description="Macros needed to make an instance of this"
    )
    children: List[ConfigUnion] = Field(
        ..., description="The Channels, Groups and Child Devices to instantiate"
    )
