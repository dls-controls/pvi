import re
from typing import Iterator, Union

from ._types import Component, Group, T, Tree


def truncate_description(desc: str) -> str:
    """Take the first line of a multiline description, truncated to 40 chars"""
    first_line = desc.strip().split("\n")[0]
    return first_line[:40]


def walk(tree: Tree[T]) -> Iterator[Union[T, Group[T]]]:
    """Depth first traversal of tree"""
    for t in tree:
        yield t
        if isinstance(t, Group):
            yield from walk(t.children)


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


def get_label(component: Component) -> str:
    """If the component has a label, use that, otherwise
    return the Title Case version of its camelCase name"""
    label = component.label
    if label is None:
        label = camel_to_title(component.name)
    return label
