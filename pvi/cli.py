from argparse import ArgumentParser
from pathlib import Path

from ._schema import PVISchema
from ._types import Formatter

SUFFIXES = ["." + x[7:] for x in Formatter.__dict__ if x.startswith("format_")]


def schema(args):
    with open(args.json, "w") as f:
        f.write(PVISchema.schema_json(indent=args.indent))


def generate(args):
    suffix = args.out.suffix
    assert suffix in SUFFIXES, f"File suffix '{suffix}' is not one of {SUFFIXES}"
    name = args.yaml.name
    assert name.endswith(".pvi.yaml"), "Expected '{name}' to end with '.pvi.yaml'"
    basename = name[:-9]
    schema = PVISchema.load(args.yaml.parent, basename)
    if suffix == ".template":
        tree = schema.producer.produce_records(schema.components)
    elif suffix in (".cpp", ".h"):
        tree = schema.producer.produce_asyn_parameters(schema.components)
    else:
        tree = schema.producer.produce_channels(schema.components)
    format = getattr(schema.formatter, f"format_{suffix[1:]}")
    text = format(tree, basename, schema.macros)
    with open(args.out, "w") as f:
        f.write(text)


def main(args=None):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    # Add a command for interatcting with the schema
    sub = subparsers.add_parser(
        "schema", help="Output JSON schema for pvi YAML format to file"
    )
    sub.add_argument("json", type=Path, help="path to the JSON output file")
    sub.set_defaults(func=schema)
    sub.add_argument(
        "-i", "--indent", type=int, default=2, help="indent level for JSON"
    )
    # Add a command for generating produces
    sub = subparsers.add_parser("generate", help="Generate one of the products")
    sub.set_defaults(func=generate)
    sub.add_argument("yaml", type=Path, help="path to the YAML source file")
    sub.add_argument(
        "out",
        type=Path,
        help=f"path to the output file to produce with suffix in {SUFFIXES}",
    )
    # Parse args and return
    args = parser.parse_args(args)
    args.func(args)
