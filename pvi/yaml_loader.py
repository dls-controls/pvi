import importlib
from annotypes import Any, TYPE_CHECKING
from ruamel import yaml

if TYPE_CHECKING:
    from typing import List, Callable, Dict, Tuple


# Taken from malcolm
# file: yamlutil.py
# class.method: Section.instantiate
def lookup_component(component_type, filename, lineno):
    # type: (str, str, int) -> Callable[..., List[Any]]

    pkg, ident = component_type.rsplit(".", 1)
    # TODO: the hardcoded "pvi.modules." string below will eventually be a
    #  variable and supplied by a Producer instance
    pkg = "pvi.modules.%s" % pkg

    try:
        ob = importlib.import_module(pkg)
    except ImportError as e:
        print("\n%s: %d: \n%s" % (filename, lineno, e))

    try:
        ob = getattr(ob, ident)
    except AttributeError:
        print("\n%s:%d:\nPackage %s has no ident %s" %
              (filename, lineno, pkg, ident))

    return ob


def get_component_yaml_info(yaml_path):
    # type: (str) -> List[Tuple[str, str, int, Dict]]
    with open(yaml_path) as f:
        text = f.read()

    code = yaml.load(text, Loader=yaml.RoundTripLoader)
    components_section = code["components"]
    components_and_info = []

    for component_info in components_section:
        pos_info = component_info.lc.key("type")
        lineno = pos_info[0]
        component_type = component_info.pop("type")
        components_and_info.append((component_type, yaml_path, lineno,
                                    component_info))

    return components_and_info


def get_intermediate_objects(info):
    # type: (List[Tuple[str, str, int, Dict]]) -> List[Any]
    intermediate_objects = []

    for component_type, yaml_path, lineno, component_info in info:
        component = lookup_component(component_type, yaml_path, lineno)
        intermediate_objects += component(**component_info)

    return intermediate_objects