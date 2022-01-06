from __future__ import annotations

from .._measures.generic_measure import GenericMeasure
from ..measure_description import (
    MeasureDescription,
    MeasureLike,
    _convert_to_measure_description,
)


def concat(*measures: MeasureLike, separator: str = "") -> MeasureDescription:
    """Concatenate measures together into a string.

    Args:
        measures: The string measures to concatenate together.
        separator: The separator to place between each measure value.
    """
    underlying_measures = [
        _convert_to_measure_description(measure) for measure in measures
    ]
    return GenericMeasure("STRING_CONCAT", separator, underlying_measures)
