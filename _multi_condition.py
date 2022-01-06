from __future__ import annotations

from dataclasses import dataclass, field
from typing import Collection, Optional

from ._condition import Condition
from ._hierarchy_isin_conditions import HierarchyIsInCondition
from ._level_conditions import LevelCondition
from ._level_isin_conditions import LevelIsInCondition
from ._measures.boolean_measure import BooleanMeasure
from .measure_description import MeasureConvertible


@dataclass(frozen=True)
class MultiCondition(Condition, MeasureConvertible):
    """Multiple Condition class, used to combine multiple level conditions."""

    _level_conditions: Collection[LevelCondition] = field(default_factory=tuple)
    _measure_conditions: Collection[BooleanMeasure] = field(default_factory=tuple)
    _level_isin_conditions: Collection[LevelIsInCondition] = field(
        default_factory=tuple
    )
    _hierarchy_isin_condition: Collection[HierarchyIsInCondition] = field(
        default_factory=tuple
    )

    def __and__(self, other: Condition) -> MultiCondition:
        """Override the ``&`` bitwise operator.

        This allows the combination of measure-filtering conditions.

        Args:
            other: The other condition to merge with this one

        """
        if isinstance(other, BooleanMeasure):
            return MultiCondition(
                self._level_conditions,
                tuple(self._measure_conditions) + (other,),
                self._level_isin_conditions,
                self._hierarchy_isin_condition,
            )

        if isinstance(other, LevelCondition):
            return MultiCondition(
                tuple(self._level_conditions) + (other,),
                self._measure_conditions,
                self._level_isin_conditions,
                self._hierarchy_isin_condition,
            )

        if isinstance(other, LevelIsInCondition):
            return MultiCondition(
                self._level_conditions,
                self._measure_conditions,
                tuple(self._level_isin_conditions) + (other,),
                self._hierarchy_isin_condition,
            )

        if isinstance(other, HierarchyIsInCondition):
            return MultiCondition(
                self._level_conditions,
                self._measure_conditions,
                self._level_isin_conditions,
                tuple(self._hierarchy_isin_condition) + (other,),
            )

        if isinstance(other, MultiCondition):
            return MultiCondition(
                tuple(self._level_conditions) + tuple(other._level_conditions),
                tuple(self._measure_conditions) + tuple(other._measure_conditions),
                tuple(self._level_isin_conditions)
                + tuple(other._level_isin_conditions),
                tuple(self._hierarchy_isin_condition)
                + tuple(other._hierarchy_isin_condition),
            )

        raise ValueError("Invalid condition provided.")

    def _to_measure_description(
        self,
        agg_fun: Optional[str] = None,  # pylint: disable=unused-argument
    ) -> BooleanMeasure:
        """Convert this object into a measure.

        Transforms all of the level conditions into measures and return the logical conjunction of all the values.
        """
        measures = list(self._measure_conditions)
        for level_condition in self._level_conditions:
            measures.append(level_condition._to_measure_description())

        for level_isin_condition in self._level_isin_conditions:
            measures.append(level_isin_condition._to_measure_description())

        for hierarchy_isin_condition in self._hierarchy_isin_condition:
            measures.append(hierarchy_isin_condition._to_measure_description())

        from ._functions.measure import conjunction

        return conjunction(*measures)
