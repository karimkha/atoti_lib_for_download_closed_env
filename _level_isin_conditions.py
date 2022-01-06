from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Collection, Optional

from ._condition import Condition

if TYPE_CHECKING:
    from ._base._base_level import BaseLevel
    from ._measures.boolean_measure import BooleanMeasure
    from ._multi_condition import MultiCondition


@dataclass(frozen=True)
class LevelIsInCondition(Condition):
    """Class for isin condition on cube levels."""

    _level: BaseLevel
    _members: Collection[Any]
    _operation: str = "li"

    def __and__(self, other: Condition) -> MultiCondition:
        """Override the ``&`` bitwise operator to allow users to combine conditions."""
        from ._level_conditions import LevelCondition
        from ._measures.boolean_measure import BooleanMeasure
        from ._multi_condition import MultiCondition

        if isinstance(other, BooleanMeasure):
            return MultiCondition(
                _level_isin_conditions=(self,), _measure_conditions=(other,)
            )

        if isinstance(other, LevelCondition):
            return MultiCondition(
                _level_isin_conditions=(self,), _level_conditions=(other,)
            )

        if isinstance(other, LevelIsInCondition):
            return MultiCondition(_level_isin_conditions=(self, other))

        if isinstance(other, MultiCondition):
            return MultiCondition(
                other._level_conditions,
                other._measure_conditions,
                tuple(other._level_isin_conditions) + (self,),
                other._hierarchy_isin_condition,
            )

        raise ValueError("Invalid condition provided.")

    def _to_measure_description(
        self,
        agg_fun: Optional[str] = None,  # pylint: disable=unused-argument
    ) -> BooleanMeasure:
        """Convert this object into a boolean measure.

        Args:
            agg_fun: The aggregation function.

        """
        from ._measures.boolean_measure import BooleanMeasure
        from .query.level import QueryLevel

        if isinstance(self._level, QueryLevel):
            raise ValueError("Query level conditions cannot be converted to measures")

        if len(self._members) == 1:
            return (self._level == list(self._members)[0])._to_measure_description()

        return BooleanMeasure(
            "or",
            [
                (self._level == value)._to_measure_description()
                for value in self._members
            ],
        )
