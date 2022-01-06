from __future__ import annotations

import datetime
from typing import Union

from typing_extensions import Literal

from .._measures.calculated_measure import CalculatedMeasure, Operator
from ..measure_description import (
    MeasureConvertible,
    MeasureDescription,
    _convert_to_measure_description,
)

DateOrMeasure = Union[
    MeasureDescription, MeasureConvertible, datetime.date, datetime.datetime
]

_Unit = Literal[  # pylint: disable=invalid-name
    "seconds", "minutes", "hours", "days", "weeks", "months", "years"
]


def date_diff(
    from_date: DateOrMeasure,
    to_date: DateOrMeasure,
    *,
    unit: _Unit = "days",
) -> MeasureDescription:
    """Return a measure equal to the difference between two dates.

    If one of the date is ``N/A`` then ``None`` is returned.

    Args:
        from_date: The first date measure or object.
        to_date: The second date measure or object.
        unit: The difference unit.
            Seconds, minutes and hours are only allowed if the dates contain time information.

    Example:
        >>> from datetime import date
        >>> df = pd.DataFrame(
        ...     columns=["From", "To"],
        ...     data=[
        ...         (date(2020, 1, 1), date(2020, 1, 2)),
        ...         (date(2020, 2, 1), date(2020, 2, 21)),
        ...         (date(2020, 3, 20), None),
        ...         (date(2020, 5, 15), date(2020, 4, 15)),
        ...     ],
        ... )
        >>> table = session.read_pandas(
        ...     df,
        ...     table_name="date_diff example",
        ... )
        >>> cube = session.create_cube(table)
        >>> l, m = cube.levels, cube.measures
        >>> m["Diff"] = tt.date_diff(l["From"], l["To"])
        >>> cube.query(m["Diff"], m["contributors.COUNT"], levels=[l["From"], l["To"]])
                              Diff contributors.COUNT
        From       To
        2020-01-01 2020-01-02    1                  1
        2020-02-01 2020-02-21   20                  1
        2020-03-20 N/A                              1
        2020-05-15 2020-04-15  -30                  1

    """
    return CalculatedMeasure(
        Operator(
            "datediff",
            [
                _convert_to_measure_description(from_date),
                _convert_to_measure_description(to_date),
                unit,
            ],
        )
    )
