from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from atoti._measures.utils import convert_level_in_description

from ..cube import Cube
from ..level import Level
from ..measure_description import MeasureDescription

if TYPE_CHECKING:
    from .._java_api import JavaApi


@dataclass(eq=False)
class LevelMeasure(MeasureDescription):
    """Measure based on a cube level."""

    _level: Level

    def _get_level(self, cube: Cube) -> Level:
        """Dynamically fetch the level in case it has been updated."""
        return cube.levels[(self._level.hierarchy, self._level.name)]

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        distilled_name = java_api.create_measure(
            cube,
            measure_name,
            "LEVEL",
            list(convert_level_in_description((self._get_level(cube),)))[0],
        )
        return distilled_name
