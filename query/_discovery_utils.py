from __future__ import annotations

from typing import TYPE_CHECKING

from .._mappings import ImmutableMapping
from ._discovery import Discovery, DiscoveryCube, DiscoveryHierarchy
from .cube import QueryCube
from .cubes import QueryCubes
from .hierarchies import QueryHierarchies
from .hierarchy import QueryHierarchy
from .level import QueryLevel
from .measure import QueryMeasure
from .measures import QueryMeasures

if TYPE_CHECKING:
    from .session import QuerySession


def _create_hierarchy(
    dimension_name: str, discovery_hierarchy: DiscoveryHierarchy
) -> QueryHierarchy:
    levels = ImmutableMapping(
        {
            level["name"]: QueryLevel(
                level["name"], dimension_name, discovery_hierarchy["name"]
            )
            for level in discovery_hierarchy["levels"]
            if level["type"] != "ALL"
        }
    )
    return QueryHierarchy(
        discovery_hierarchy["name"],
        dimension_name,
        levels,
        discovery_hierarchy["slicing"],
    )


def _create_cube(
    discovery_cube: DiscoveryCube,
    session: QuerySession,
) -> QueryCube:
    hierarchies = QueryHierarchies(
        {
            (dimension["name"], hierarchy["name"]): _create_hierarchy(
                dimension["name"], hierarchy
            )
            for dimension in discovery_cube["dimensions"]
            if dimension["name"] != "Epoch"
            for hierarchy in dimension["hierarchies"]
        }
    )
    measures = QueryMeasures(
        {
            measure["name"]: QueryMeasure(
                measure["name"],
                measure["visible"],
                measure.get("folder"),
                measure.get("formatString"),
                measure.get("description"),
            )
            for measure in discovery_cube["measures"]
        }
    )
    return QueryCube(discovery_cube["name"], hierarchies, measures, session)


def create_cubes_from_discovery(
    discovery: Discovery,
    session: QuerySession,
) -> QueryCubes:
    """Return a mapping of all the cubes in the discovery.

    Args:
        discovery: The Discovery containing the cubes' data.
        session: The parent session.
    """
    return QueryCubes(
        {
            cube["name"]: _create_cube(cube, session)
            for catalog in discovery["catalogs"]
            for cube in catalog["cubes"]
        }
    )
