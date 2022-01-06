from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Sequence, Union

from ..measure_description import MeasureDescription
from ..scope._utils import LeafLevels
from .utils import convert_measure_args

if TYPE_CHECKING:
    from .._java_api import JavaApi
    from ..cube import Cube

Operand = Union[MeasureDescription, str]


@dataclass(frozen=True)
class Operator:
    """An operator to create a calculated measure from other measures."""

    _name: str
    _operands: Sequence[Operand]

    @staticmethod
    def mul(operands: Sequence[MeasureDescription]) -> Operator:
        """Multiplication operator."""
        return Operator("mul", operands)

    @staticmethod
    def truediv(operands: Sequence[MeasureDescription]) -> Operator:
        """Division operator."""
        return Operator("truediv", operands)

    @staticmethod
    def floordiv(operands: Sequence[MeasureDescription]) -> Operator:
        """Division operator."""
        return Operator("floordiv", operands)

    @staticmethod
    def add(operands: Sequence[MeasureDescription]) -> Operator:
        """Addition operator."""
        return Operator("add", operands)

    @staticmethod
    def sub(operands: Sequence[MeasureDescription]) -> Operator:
        """Subtraction operator."""
        return Operator("sub", operands)

    @staticmethod
    def neg(operand: MeasureDescription) -> Operator:
        """Neg operator."""
        return Operator("neg", [operand])

    @staticmethod
    def mod(operands: Sequence[MeasureDescription]) -> Operator:
        """Modulo operator."""
        return Operator("mod", operands)


@dataclass(eq=False)
class CalculatedMeasure(MeasureDescription):
    """A calculated measure is the result of an operation between other measures."""

    _operator: Operator

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        return java_api.create_measure(
            cube,
            measure_name,
            "CALCULATED",
            self._operator._name,
            convert_measure_args(
                java_api=java_api,
                cube=cube,
                args=self._operator._operands,
            ),
        )


@dataclass(eq=False)
class AggregatedMeasure(MeasureDescription):
    """Aggregated Measure."""

    _underlying_measure: MeasureDescription
    _agg_fun: str
    _on_levels: Optional[LeafLevels]

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        underlying_name = self._underlying_measure._distil(java_api=java_api, cube=cube)

        distilled_name = java_api.create_measure(
            cube,
            measure_name,
            "LEAF_AGGREGATION",
            underlying_name,
            self._on_levels.levels if self._on_levels else [],
            self._agg_fun,
        )
        return distilled_name
