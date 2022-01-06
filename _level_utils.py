from typing import Any, Iterable

from ._base._base_hierarchy import BaseHierarchy


def raise_multiple_levels_error(
    level_name: str, hierarchies: Iterable[BaseHierarchy[Any]]
):
    raise KeyError(
        f"""Multiple levels are named {level_name}. Specify the hierarchy (and the dimension if necessary): {", ".join([
            f'cube.levels["{hierarchy.dimension}", "{hierarchy.name}", "{level_name}"]'
            for hierarchy in hierarchies
        ])}"""
    )
