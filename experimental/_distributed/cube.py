from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterable

from typeguard import typeguard_ignore

from ..._local_cube import LocalCube
from ...aggregates_cache import AggregatesCache
from ...query._cellset import LevelCoordinates
from .hierarchies import DistributedHierarchies
from .levels import DistributedLevels
from .measures import DistributedMeasures

if TYPE_CHECKING:
    from ..._java_api import JavaApi
    from .session import DistributedSession


class DistributedCube(
    LocalCube[DistributedHierarchies, DistributedLevels, DistributedMeasures]
):
    """Cube of a distributed session."""

    @typeguard_ignore
    def __init__(self, name: str, *, java_api: JavaApi, session: DistributedSession):
        """Init."""
        super().__init__(
            name=name,
            java_api=java_api,
            session=session,
            hierarchies=DistributedHierarchies(java_api, self),
            level_function=lambda hierarchies: DistributedLevels(hierarchies),
            measures=DistributedMeasures(java_api, self),
            agg_cache=AggregatesCache(java_api, self),
        )

    def _get_level_data_types(  # pylint: disable=no-self-use
        self, levels_coordinates: Iterable[LevelCoordinates]
    ) -> Dict[LevelCoordinates, str]:
        return {level_coordinates: "object" for level_coordinates in levels_coordinates}
