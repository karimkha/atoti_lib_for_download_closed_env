from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from .measure_description import MeasureConvertible

if TYPE_CHECKING:
    from ._measures.boolean_measure import BooleanMeasure


class Condition(MeasureConvertible):
    """ABC for conditions which will be used to filter measures."""

    @abstractmethod
    def __and__(self, other: Condition) -> Condition:
        """Override the & bitwise operator to allow users to combine conditions."""

    def __xor__(self, other: Condition) -> Condition:
        """Throw an exception if the user tries to perform a xor condition."""
        raise Exception("XOR conditions are not supported.")

    def __invert__(self) -> BooleanMeasure:
        """Override the ~ bitwise operator.

        This allows the user to write more complicated conditions when filtering.

        Since Python's built-in ``not`` cannot be overridden to return anything other than a boolean value, the ``~`` bitwise operator is used to reverse the value of a condition.
        """
        from ._measures.boolean_measure import BooleanMeasure

        return BooleanMeasure("invert", [self._to_measure_description()])

    def __or__(self, other: Condition) -> BooleanMeasure:
        """Override the | bitwise operator to allow users to combine conditions."""
        from ._measures.boolean_measure import BooleanMeasure

        return BooleanMeasure(
            "or", [self._to_measure_description(), other._to_measure_description()]
        )

    def _get_bool_alternative_message(self) -> str:  # pylint: disable=no-self-use
        return "To combine conditions, use the bitwise operators `&` or `|` instead of the keywords `and` or `or`."
