from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from typeguard import typechecked, typeguard_ignore

from ._base._base_level import BaseLevel
from ._level_conditions import LevelCondition
from ._repr_utils import ReprJson
from .comparator import ASCENDING, Comparator
from .measure_description import MeasureConvertible, MeasureDescription
from .type import DataType

if TYPE_CHECKING:
    from .hierarchy import Hierarchy


@typeguard_ignore
@dataclass(eq=False)
class Level(BaseLevel, MeasureConvertible):
    """Level of a :class:`~atoti.hierarchy.Hierarchy`.

    A level is a sub category of a hierarchy.
    Levels have a specific order with a parent-child relationship.

    In a :guilabel:`Pivot Table`, a single-level hierarchy will be displayed as a flat attribute while a multi-level hierarchy will display the first level and allow users to expand each member against the next level and display sub totals.

    For example, a :guilabel:`Geography` hierarchy can have a :guilabel:`Continent` as the top level where :guilabel:`Continent` expands to :guilabel:`Country` which in turns expands to the leaf level: :guilabel:`City`.
    """

    _column_name: str
    _data_type: DataType
    _hierarchy: Optional[Hierarchy] = None
    _comparator: Comparator = ASCENDING

    @property
    def dimension(self) -> str:
        """Name of the dimension holding the level."""
        if self._hierarchy is None:
            raise ValueError(f"Missing hierarchy for level {self.name}.")
        return self._hierarchy.dimension

    @property
    def hierarchy(self) -> str:
        """Name of the hierarchy holding the level."""
        if self._hierarchy is None:
            raise ValueError(f"Missing hierarchy for level {self.name}.")
        return self._hierarchy.name

    @property
    def data_type(self) -> DataType:
        """Type of the level members."""
        return self._data_type

    @property
    def comparator(self) -> Comparator:  # noqa: D401
        """Comparator of the level."""
        return self._comparator

    @comparator.setter
    @typechecked
    def comparator(self, value: Comparator) -> None:  # noqa: D401
        """Comparator setter."""
        if self._hierarchy is None:
            raise ValueError(f"Missing hierarchy for level {self.name}.")
        self._comparator = value
        self._hierarchy._java_api.update_level_comparator(self)
        self._hierarchy._java_api.refresh()

    def _to_measure_description(
        self, agg_fun: Optional[str] = None
    ) -> MeasureDescription:
        """Convert this column into a measure."""
        from ._measures.level_measure import LevelMeasure

        if agg_fun is not None:
            from ._measures.calculated_measure import AggregatedMeasure
            from .scope import LeafLevels

            return AggregatedMeasure(LevelMeasure(self), agg_fun, LeafLevels([self]))
        return LevelMeasure(self)

    def _repr_json_(self) -> ReprJson:
        data = {
            "dimension": self.dimension,
            "hierarchy": self.hierarchy,
            "type": str(self.data_type),
        }
        if self.comparator is not None:
            data["comparator"] = self.comparator._name
        return (data, {"expanded": True, "root": self.name})

    def __ne__(
        self, other: Any
    ) -> LevelCondition:  # pyright: reportIncompatibleMethodOverride=false
        """Return a non-equality condition against this level."""
        if isinstance(other, MeasureDescription):
            return NotImplemented
        return LevelCondition(self, other, "ne")

    def __lt__(self, other: Any) -> LevelCondition:
        """Return a less than condition against this level."""
        if isinstance(other, MeasureDescription):
            return NotImplemented
        return LevelCondition(self, other, "lt")

    def __le__(self, other: Any) -> LevelCondition:
        """Return a less or equals condition against this level."""
        if isinstance(other, MeasureDescription):
            return NotImplemented
        return LevelCondition(self, other, "le")

    def __gt__(self, other: Any) -> LevelCondition:
        """Return a greater than condition against this level."""
        if isinstance(other, MeasureDescription):
            return NotImplemented
        return LevelCondition(self, other, "gt")

    def __ge__(self, other: Any) -> LevelCondition:
        """Return a greater or equal condition against this level."""
        if isinstance(other, MeasureDescription):
            return NotImplemented
        return LevelCondition(self, other, "ge")
