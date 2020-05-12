import csv
import io
from io import StringIO
from typing import List

from ruamel.yaml import YAML

from ._types import AsynParameter, Formatter, Group, Record, Tree
from ._util import prepare_for_yaml
from .another_repo import DeviceConfig, walk

FIELD_TXT = '    field({0:5s} "{1}")\n'
INFO_TXT = '    info({0} "{1}")\n'


class DLSFormatter(Formatter):
    def format_edl(self, device: DeviceConfig, basename: str) -> str:
        raise NotImplementedError(self)

    def format_yaml(self, device: DeviceConfig, basename: str) -> str:
        # Walk the tree stripping enums and preserving descriptions
        prepared_device = prepare_for_yaml(device.dict())
        stream = StringIO()
        YAML().dump(prepared_device, stream)
        return stream.getvalue()

    def format_csv(self, device: DeviceConfig, basename: str) -> str:
        out = io.StringIO(newline="")
        writer = csv.writer(out, delimiter=",", quotechar='"')
        writer.writerow(["Parameter", "PVs", "Description"])
        for channel in walk(device.children):
            if isinstance(channel, Group):
                writer.writerow([f"*{channel.name}*"])
            else:
                # Filter out PVs that are None
                pvs = "\n".join(filter(None, [channel.write_pv, channel.read_pv]))
                writer.writerow([channel.name, pvs, channel.description])
        return out.getvalue()

    def format_template(self, records: Tree[Record], basename: str) -> str:
        txt = ""
        for record in walk(records):
            if isinstance(record, Group):
                txt += f"# Group: {record.name}\n\n"
            else:
                fields = ""
                for k, v in record.fields_.items():
                    fields += FIELD_TXT.format(k + ",", v)
                for k, v in record.infos.items():
                    fields += INFO_TXT.format(k + ",", v)
                txt += f"""\
record({record.type}, "{record.name}") {{
{fields.rstrip()}
}}

"""
        return txt

    def format_h(self, parameters: Tree[AsynParameter], basename: str) -> str:
        parameter_members = ""
        for parameter in walk(parameters):
            if isinstance(parameter, Group):
                parameter_members += f"/* Group: {parameter.name} */\n"
            else:
                parameter_members += (
                    f"    int {parameter.name};  "
                    f"/* {parameter.type} {parameter.description} */\n"
                )
        h_txt = f"""\
#ifndef {basename.upper()}_PARAMETERS_H
#define {basename.upper()}_PARAMETERS_H

class {basename.title()}Parameters {{
public:
    {basename.title()}Parameters(asynPortDriver *parent);
    {parameter_members.rstrip()}
}}

#endif //{basename.upper()}_PARAMETERS_H
"""
        return h_txt

    def format_cpp(self, parameters: Tree[AsynParameter], basename: str) -> str:
        create_params = ""
        for parameter in walk(parameters):
            if isinstance(parameter, AsynParameter):
                create_params += (
                    f'    parent->createParam("{parameter.name}", '
                    f"{parameter.type}, &{parameter.name});\n"
                )
        cpp_txt = f"""\
{basename.title()}Parameters::{basename.title()}Parameters(asynPortDriver *parent) {{
{create_params.rstrip()}
}}
"""
        return cpp_txt
