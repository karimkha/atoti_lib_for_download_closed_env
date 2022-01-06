from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Mapping, Tuple, Union

from typeguard import typechecked, typeguard_ignore

from ..._base._base_hierarchies import _HierarchyKey
from ..._local_hierarchies import LocalHierarchies
from ..._mappings import ImmutableMapping
from ...hierarchy import Hierarchy
from ...level import Level
from ...query.hierarchy import QueryHierarchy
from ...query.level import QueryLevel

if TYPE_CHECKING:
    from ...table import Column
    from .cube import DistributedCube

    LevelOrColumn = Union[Level, Column]


def _cube_hierarchy_to_query_hierarchy(hierarchy: Hierarchy) -> QueryHierarchy:
    """Convert a cube hierarchy into a query hierarchy."""
    return QueryHierarchy(
        hierarchy.name,
        hierarchy.dimension,
        to_query_levels(hierarchy.levels),
        hierarchy.slicing,
    )


def _cube_level_to_query_level(level: Level) -> QueryLevel:
    """Convert a cube level into a query level."""
    return QueryLevel(level.name, level.dimension, level.hierarchy)


def to_query_levels(levels: Mapping[str, Level]) -> ImmutableMapping[str, QueryLevel]:
    """Convert a dict of cube levels into a dict of query levels."""
    return ImmutableMapping(
        {
            levelName: _cube_level_to_query_level(levels[levelName])
            for levelName in levels
            if levelName != "ALL"
        }
    )


@typeguard_ignore
@dataclass(frozen=True)
class DistributedHierarchies(
    LocalHierarchies[QueryHierarchy],
):
    """Manage the hierarchies."""

    _cube: DistributedCube = field(repr=False)

    def _get_underlying(self) -> Dict[Tuple[str, str], QueryHierarchy]:
        hierarchies = self._retrieve_hierarchies(self._java_api, self._cube)
        return {
            hierarchyCoordinate: _cube_hierarchy_to_query_hierarchy(
                hierarchies[hierarchyCoordinate]
            )
            for hierarchyCoordinate in hierarchies
        }

    @typechecked
    def __getitem__(self, key: _HierarchyKey) -> QueryHierarchy:
        (dimension_name, hierarchy_name) = self._convert_key(key)
        cube_hierarchies = self._java_api.retrieve_hierarchy(
            hierarchy_name, cube=self._cube, dimension=dimension_name
        )
        hierarchies = [_cube_hierarchy_to_query_hierarchy(h) for h in cube_hierarchies]
        if len(hierarchies) == 0:
            raise KeyError(f"Unknown hierarchy: {key}")
        if len(hierarchies) == 1:
            return hierarchies[0]
        raise self._multiple_hierarchies_error(key, hierarchies)
