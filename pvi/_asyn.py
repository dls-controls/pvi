from enum import Enum
from typing import Any, ClassVar, List, Union

from pydantic import BaseModel, Field

from pvi._types import ChannelConfig, DisplayForm, Widget

from ._records import (
    AnalogueAll,
    BinaryAll,
    LongAll,
    MultiBitBinaryAll,
    StringAll,
    WaveformAll,
)
from ._types import AsynParameter, Component, Producer, Record, Tree
from ._util import truncate_description


class TypeStrings(BaseModel):
    read_record: str = Field(..., description="e.g. ai, bi, longin")
    write_record: str = Field(..., description="e.g. ao, bo, longout")
    asyn_read: str = Field(..., description="e.g. asynInt32, asynOctetRead")
    asyn_write: str = Field(..., description="e.g. asynInt32, asynOctetWrite")
    asyn_param: str = Field(..., description="e.g. asynParamInt32, asynParamOctet")


class ParameterRole(str, Enum):
    """What role does this parameter play within the device. One of:

    - Readback: a parameter of the device that can be read from.
      E.g. chipTemperature on a detector, or isHomed for a motor
    - Action: a parameter of the device that can be written to, but there
      is no current value.
      E.g. reboot on a detector, or overwriteCurrentPosition for a motor
    - Setting: a parameter of the device that can be written to, the
      current value can be read from, and should be saved/loaded when
      switching between configurations of the device.
      E.g. acquireTime on a detector, or velocity of a motor
    - Transient: a parameter of the device that can be written to and
      read from, but should not be saved/loaded when switching between
      configurations of the device.
      E.g. arrayCounter on a detector, or position of a motor
    """

    READBACK = "Readback"  #: Read record only
    ACTION = "Action"  #: Write record only
    SETTING = "Setting"  #: Read and write record, for saving
    TRANSIENT = "Transient"  #: Read and write record, not for saving

    def needs_read_record(self):
        return self != self.ACTION

    def needs_write_record(self):
        return self != self.READBACK


class ScanRate(str, Enum):
    PASSIVE = "Passive"
    EVENT = "Event"
    IOINTR = "I/O Intr"
    TEN = "10 second"
    FIVE = "5 second"
    TWO = "2 second"
    ONE = "1 second"
    POINTFIVE = ".5 second"
    POINTTWO = ".2 second"
    POINTONE = ".1 second"


class AsynComponent(Component):
    """Base class for all Asyn Parameters to inherit from"""

    description: str = Field(
        ..., description="Description of what this Parameter is for"
    )
    role: ParameterRole = Field(
        ParameterRole.SETTING, description=ParameterRole.__doc__,
    )
    demand_auto_updates: bool = Field(
        False, description="Should demand update when readback changes?"
    )
    autosave: List[str] = Field(
        [], description="Record fields that should be autosaved"
    )
    read_record_suffix: str = Field(
        None, description="The read record suffix, if not given then use $(name)_RBV"
    )
    read_record_scan: ScanRate = Field(
        ScanRate.IOINTR, description="SCAN rate of the read record"
    )
    write_record_suffix: str = Field(
        None, description="The write record suffix, if not given then use $(name)"
    )
    display_form: DisplayForm = Field(
        None, description="Display form for numeric/array fields"
    )
    type_strings: ClassVar[TypeStrings]
    initial: Any
    read_widget: Widget
    write_widget: Widget
    record_fields: Any


def initial_field(**kwargs):
    return Field(None, description="The initial value of the parameter", **kwargs)


def widget_field(default: Widget, **kwargs):
    return Field(
        default,
        description="Override the widget to use these sort of channels",
        **kwargs,
    )


class AsynBinary(AsynComponent):
    """Asyn Float32 Parameter and records"""

    type_strings: ClassVar[TypeStrings] = TypeStrings(
        read_record="bi",
        write_record="bo",
        asyn_read="asynInt32",
        asyn_write="asynInt32",
        asyn_param="asynParamInt32",
    )
    initial: int = initial_field(ge=0, le=1)
    read_widget: Widget = widget_field(Widget.LED)
    write_widget: Widget = widget_field(Widget.CHECKBOX)
    record_fields: BinaryAll = Field(BinaryAll(), description="Binary record fields")


class AsynBusy(AsynComponent):
    """Asyn busy Parameter and records"""

    type_strings: ClassVar[TypeStrings] = TypeStrings(
        read_record="bi",
        write_record="busy",
        asyn_read="asynInt32",
        asyn_write="asynInt32",
        asyn_param="asynParamInt32",
    )
    initial: int = initial_field(ge=0, le=1)
    read_widget: Widget = widget_field(Widget.LED)
    write_widget: Widget = widget_field(Widget.BUTTON)
    record_fields: BinaryAll = Field(
        BinaryAll(), description="Binary record fields",
    )


class AsynFloat64(AsynComponent):
    """Asyn Float64 Parameter and records"""

    type_strings: ClassVar[TypeStrings] = TypeStrings(
        read_record="ai",
        write_record="ao",
        asyn_read="asynFloat64",
        asyn_write="asynFloat64",
        asyn_param="asynParamFloat64",
    )
    initial: float = initial_field()
    read_widget: Widget = widget_field(Widget.TEXTUPDATE)
    write_widget: Widget = widget_field(Widget.TEXTINPUT)
    record_fields: AnalogueAll = Field(
        AnalogueAll(), description="Analogue record fields",
    )


class AsynInt32(AsynComponent):
    """Asyn Int32 Parameter and records"""

    type_strings: ClassVar[TypeStrings] = TypeStrings(
        read_record="ai",
        write_record="ao",
        asyn_read="asynInt32",
        asyn_write="asynInt32",
        asyn_param="asynParamInt32",
    )
    initial: int = initial_field()
    read_widget: Widget = widget_field(Widget.TEXTUPDATE)
    write_widget: Widget = widget_field(Widget.TEXTINPUT)
    record_fields: AnalogueAll = Field(
        AnalogueAll(), description="Analogue record fields",
    )


class AsynLong(AsynComponent):
    """Asyn Long Parameter and records"""

    type_strings: ClassVar[TypeStrings] = TypeStrings(
        read_record="longin",
        write_record="longout",
        asyn_read="asynInt32",
        asyn_write="asynInt32",
        asyn_param="asynParamInt32",
    )
    initial: int = initial_field()
    read_widget: Widget = widget_field(Widget.TEXTUPDATE)
    write_widget: Widget = widget_field(Widget.TEXTINPUT)
    record_fields: LongAll = Field(
        LongAll(), description="Long record fields",
    )


class AsynMultiBitBinary(AsynComponent):
    """Asyn MultiBitBinary Parameter and records"""

    type_strings: ClassVar[TypeStrings] = TypeStrings(
        read_record="mbbi",
        write_record="mbbo",
        asyn_read="asynInt32",
        asyn_write="asynInt32",
        asyn_param="asynParamInt32",
    )
    initial: int = initial_field(ge=0, le=15)
    read_widget: Widget = widget_field(Widget.TEXTUPDATE)
    write_widget: Widget = widget_field(Widget.COMBO)
    record_fields: MultiBitBinaryAll = Field(
        MultiBitBinaryAll(), description="Multi-bit binary record fields",
    )


class AsynString(AsynComponent):
    """Asyn String Parameter and records"""

    type_strings: ClassVar[TypeStrings] = TypeStrings(
        read_record="stringin",
        write_record="stringout",
        asyn_read="asynOctetRead",
        asyn_write="asynOctetWrite",
        asyn_param="asynParamOctet",
    )
    initial: str = initial_field()
    read_widget: Widget = widget_field(Widget.TEXTUPDATE)
    write_widget: Widget = widget_field(Widget.TEXTINPUT)
    record_fields: StringAll = Field(
        StringAll(), description="String record fields",
    )


class AsynWaveform(AsynComponent):
    """Asyn Waveform Parameter and records"""

    type_strings: ClassVar[TypeStrings] = TypeStrings(
        read_record="waveform",
        write_record="waveform",
        asyn_read="asynOctetRead",
        asyn_write="asynOctetWrite",
        asyn_param="asynParamOctet",
    )
    read_widget: Widget = widget_field(Widget.TEXTUPDATE)
    write_widget: Widget = widget_field(Widget.TEXTINPUT)
    record_fields: WaveformAll = Field(
        WaveformAll(), description="Waveform record fields",
    )


# Need to explicitly list the subclasses of AsynComponent here so they can be
# used in the schema to work out what components are allowed
AsynComponentUnion = Union[
    AsynBinary,
    AsynBusy,
    AsynFloat64,
    AsynInt32,
    AsynLong,
    AsynMultiBitBinary,
    AsynString,
    AsynWaveform,
]


class AsynProducer(Producer):
    prefix: str = Field(
        ..., description="The prefix for record names created by the template file"
    )
    asyn_port: str = Field(..., description="The asyn port name")
    address: str = Field(..., description="The asyn address")
    timeout: str = Field(..., description="The timeout for the asyn port")

    def _read_record_name(self, component: AsynComponent) -> str:
        if component.read_record_suffix:
            return self.prefix + component.read_record_suffix
        else:
            return self.prefix + component.name + "_RBV"

    def _write_record_name(self, component: AsynComponent) -> str:
        if component.write_record_suffix:
            return self.prefix + component.write_record_suffix
        else:
            return self.prefix + component.name

    def _make_records(self, component: AsynComponent) -> List[Record]:
        records = []
        inp_fields, out_fields = component.record_fields.sort_records()
        io = f"@asyn({self.asyn_port},{self.address},{self.timeout}){component.name}"
        if component.role.needs_read_record():
            fields = dict(
                SCAN=component.read_record_scan.value,
                DESC=truncate_description(component.description),
                INP=io,
                DTYP=component.type_strings.asyn_read,
                **inp_fields.dict(exclude_none=True),
            )
            records.append(
                Record(
                    name=self._read_record_name(component),
                    type=component.type_strings.read_record,
                    fields=fields,
                    infos={},
                )
            )
        if component.role.needs_write_record():
            fields = dict(
                DESC=truncate_description(component.description),
                DTYP=component.type_strings.asyn_write,
                **out_fields.dict(exclude_none=True),
            )
            if component.type_strings.write_record == "waveform":
                fields["INP"] = io
            else:
                fields["OUT"] = io
            if component.initial is not None:
                fields["PINI"] = "YES"
                fields["VAL"] = str(component.initial)
            infos = {}
            if component.autosave:
                infos["autosaveFields"] = " ".join(component.autosave)
            if component.demand_auto_updates:
                infos["asyn:READBACK"] = "1"
            records.append(
                Record(
                    name=self._write_record_name(component),
                    type=component.type_strings.write_record,
                    fields=fields,
                    infos=infos,
                )
            )
        return records

    def produce_records(self, components: Tree[Component]) -> Tree[Record]:
        return AsynComponent.on_each_node(components, self._make_records)

    def _make_channels(self, component: AsynComponent) -> List[ChannelConfig]:
        channels = []
        # Make the primary channel
        channel = ChannelConfig(
            name=component.name,
            label=component.get_label(),
            description=component.description,
            display_form=component.display_form,
        )
        # Add read pv
        if component.role == ParameterRole.TRANSIENT:
            # readback is a separate channel
            read_channel = ChannelConfig(
                name=component.name + "Readback",
                label=component.get_label() + " Readback",
                description=component.description,
                display_form=component.display_form,
                read_pv=self._read_record_name(component),
            )
            channels.append(read_channel)
        elif component.role.needs_read_record():
            channel.read_pv = self._read_record_name(component)
            channel.widget = component.read_widget
        # Add write pv
        if component.role.needs_write_record():
            channel.write_pv = self._write_record_name(component)
            # Write widget trumps read widget
            channel.widget = component.write_widget
        channels.append(channel)
        return channels

    def produce_channels(self, components: Tree[Component]) -> Tree[ChannelConfig]:
        return AsynComponent.on_each_node(components, self._make_channels)

    def _make_asyn_parameters(self, component: AsynComponent) -> List[AsynParameter]:
        parameter = AsynParameter(
            name=component.name,
            type=component.type_strings.asyn_param,
            description=component.role.value,
        )
        return [parameter]

    def produce_asyn_parameters(
        self, components: Tree[Component]
    ) -> Tree[AsynParameter]:
        return AsynComponent.on_each_node(components, self._make_asyn_parameters)
