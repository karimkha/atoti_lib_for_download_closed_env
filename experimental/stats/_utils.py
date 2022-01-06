from typing import Union

from ...measure_description import MeasureConvertible, MeasureDescription

NumericMeasureLike = Union[int, float, MeasureDescription, MeasureConvertible]


def ensure_strictly_positive(arg: NumericMeasureLike, arg_name: str):
    if isinstance(arg, (int, float)):
        if arg <= 0:
            raise ValueError(f"{arg_name} must be greater than 0.")
    elif not isinstance(arg, MeasureDescription):
        raise TypeError(f"{arg_name} must be a measure or an number.")
