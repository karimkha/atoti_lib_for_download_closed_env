from __future__ import annotations

from typing import List, Mapping, Optional

from typing_extensions import TypedDict

CubeName = str
DimensionName = str
HierarchyName = str


class DiscoveryLevel(TypedDict):  # noqa: D101
    caption: str
    name: str
    type: str


class DiscoveryHierarchy(TypedDict):  # noqa: D101
    levels: List[DiscoveryLevel]
    name: HierarchyName
    slicing: bool


class DiscoveryDimension(TypedDict):  # noqa: D101
    hierarchies: List[DiscoveryHierarchy]
    name: DimensionName


class DiscoveryMeasure(TypedDict):  # noqa: D101
    name: DimensionName
    visible: bool
    folder: Optional[str]
    formatter: Optional[str]
    description: Optional[str]


class DiscoveryCube(TypedDict):  # noqa: D101
    dimensions: List[DiscoveryDimension]
    measures: List[DiscoveryMeasure]
    name: CubeName


class DiscoveryCatalog(TypedDict):  # noqa: D101
    cubes: List[DiscoveryCube]


class Discovery(TypedDict):  # noqa: D101
    catalogs: List[DiscoveryCatalog]


DiscoveryHierarchyMapping = Mapping[HierarchyName, DiscoveryHierarchy]
DiscoveryDimensionMapping = Mapping[DimensionName, DiscoveryHierarchyMapping]


def _get_hierarchies_mapping(
    dimension: DiscoveryDimension,
) -> DiscoveryHierarchyMapping:
    """Make access to hierarchy by name more efficient."""
    return {hierarchy["name"]: hierarchy for hierarchy in dimension["hierarchies"]}


def get_dimensions_mapping(cube: DiscoveryCube) -> DiscoveryDimensionMapping:
    """Make access to dimension by name more efficient."""
    return {
        dimension["name"]: _get_hierarchies_mapping(dimension)
        for dimension in cube["dimensions"]
    }
