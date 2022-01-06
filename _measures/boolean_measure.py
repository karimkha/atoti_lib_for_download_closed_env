from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Sequence

from .._condition import Condition
from .._level_conditions import LevelCondition
from ..measure_description import MeasureDescription
from .utils import convert_measure_args

if TYPE_CHECKING:
    from .._java_api import JavaApi
    from .._multi_condition import MultiCondition
    from ..cube import Cube


@dataclass(eq=False)
class BooleanMeasure(MeasureDescription, Condition):
    """Boolean operation between measures."""

    _operator: str
    _operands: Sequence[MeasureDescription]

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        return java_api.create_measure(
            cube,
            measure_name,
            "BOOLEAN",
            self._operator,
            convert_measure_args(java_api=java_api, cube=cube, args=self._operands),
        )

    def __and__(self, other: Condition) -> MultiCondition:
        """Override the bitwise and (&) operator.

        This allows the user to write longer conditions when filtering.

        Args:
            other: The condition with which to merge this one.

        Returns:
            A multi condition representing the result of the & operation.

        """
        from .._multi_condition import MultiCondition

        if isinstance(other, BooleanMeasure):
            return MultiCondition(_measure_conditions=(self, other))

        if isinstance(other, LevelCondition):
            return MultiCondition(
                _level_conditions=(other,), _measure_conditions=(self,)
            )

        if isinstance(other, MultiCondition):
            return MultiCondition(
                other._level_conditions,
                tuple(other._measure_conditions) + (self,),
                other._level_isin_conditions,
                other._hierarchy_isin_condition,
            )

        raise ValueError("Invalid condition provided")

    def _to_measure_description(
        self,
        agg_fun: Optional[str] = None,  # pylint: disable=unused-argument
    ) -> BooleanMeasure:
        """Implement method for conditions."""
        return self
