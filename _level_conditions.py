from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ._condition import Condition
from .measure_description import (
    MeasureConvertible,
    MeasureLike,
    _convert_to_measure_description,
)

if TYPE_CHECKING:
    from ._base._base_level import BaseLevel
    from ._measures.boolean_measure import BooleanMeasure
    from ._multi_condition import MultiCondition


@dataclass(frozen=True)
class LevelCondition(Condition):
    """Base class for conditions on cube levels."""

    _level: BaseLevel
    _value: Optional[MeasureLike]
    _operation: str

    def __and__(self, other: Condition) -> MultiCondition:
        """Override the ``&`` bitwise operator.

        This allows the combination of filtering conditions.

        Args:
            other: The condition with which to merge this one.

        Returns:
            A multi condition representing the result of the ``&`` operation.

        """
        from ._hierarchy_isin_conditions import HierarchyIsInCondition
        from ._level_isin_conditions import LevelIsInCondition
        from ._measures.boolean_measure import BooleanMeasure
        from ._multi_condition import MultiCondition

        if isinstance(other, HierarchyIsInCondition):
            return MultiCondition(
                _level_conditions=[self], _hierarchy_isin_condition=[other]
            )

        if isinstance(other, LevelIsInCondition):
            return MultiCondition(
                _level_conditions=[self], _level_isin_conditions=[other]
            )

        if isinstance(other, BooleanMeasure):
            return MultiCondition(_level_conditions=[self], _measure_conditions=[other])

        if isinstance(other, LevelCondition):
            return MultiCondition(_level_conditions=[self, other])

        if isinstance(other, MultiCondition):
            return MultiCondition(
                tuple(other._level_conditions) + (self,),
                other._measure_conditions,
                other._level_isin_conditions,
                other._hierarchy_isin_condition,
            )

        raise ValueError("Invalid condition provided.")

    def _to_measure_description(
        self,
        agg_fun: Optional[str] = None,  # pylint: disable=unused-argument
    ) -> BooleanMeasure:
        """Convert this object into a measure.

        Args:
            agg_fun: The aggregation function.

        """
        if not isinstance(self._level, MeasureConvertible):
            raise ValueError("Query level conditions cannot be converted to measures")

        lvl_measure = _convert_to_measure_description(self._level)

        # Handle comparing to None
        if self._value is None:
            if self._operation not in ["eq", "ne"]:
                raise ValueError(f"Cannot use operation {self._operation} on None")

            from ._measures.boolean_measure import BooleanMeasure

            return (
                BooleanMeasure("isNull", [lvl_measure])
                if self._operation == "eq"
                else BooleanMeasure("notNull", [lvl_measure])
            )

        value_measure = _convert_to_measure_description(self._value)
        switcher = {
            "eq": lvl_measure == value_measure,
            "ne": lvl_measure != value_measure,
            "lt": lvl_measure < value_measure,
            "le": lvl_measure <= value_measure,
            "gt": lvl_measure > value_measure,
            "ge": lvl_measure >= value_measure,
        }
        return switcher[self._operation]
