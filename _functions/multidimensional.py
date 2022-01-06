from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Optional, Union

from py4j.protocol import JAVA_MAX_INT
from typing_extensions import Literal

from .._measures.generic_measure import GenericMeasure
from .._measures.utils import get_measure_name
from .._type_utils import is_temporal
from ..hierarchy import Hierarchy
from ..level import Level
from ..measure_description import MeasureDescription, MeasureLike

if TYPE_CHECKING:
    from typing import List, Tuple

    from .._java_api import JavaApi
    from ..cube import Cube


@dataclass(eq=False)
class ParentValue(MeasureDescription):
    """The value of the measure for the parent."""

    _underlying_measure: Union[MeasureDescription, str]
    _degrees: Mapping[Hierarchy, int]
    _total_value: Optional[MeasureLike]
    _apply_filters: bool

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        underlying_name = (
            self._underlying_measure
            if isinstance(self._underlying_measure, str)
            else get_measure_name(
                java_api=java_api, measure=self._underlying_measure, cube=cube
            )
        )
        total_measure_name = (
            self._total_value._distil(java_api=java_api, cube=cube)
            if isinstance(self._total_value, MeasureDescription)
            else None
        )
        total_literal = self._total_value if total_measure_name is None else None

        distilled_name = java_api.create_measure(
            cube,
            measure_name,
            "PARENT_VALUE",
            underlying_name,
            self._degrees,
            total_measure_name,
            total_literal,
            self._apply_filters,
        )
        return distilled_name


def parent_value(
    measure: Union[MeasureDescription, str],
    *,
    degrees: Mapping[Hierarchy, int],
    apply_filters: bool = False,
    total_value: Optional[MeasureLike] = None,
) -> MeasureDescription:
    """Return a measure equal to the passed measure at the parent member on the given hierarchies.

    Args:
        measure: The measure to take the parent value of.
        degrees: The number of levels to go up to take the value on each given hierarchy.
        apply_filters: Whether to apply the query filters on hierarchies specified in the *degrees* mapping when computing the value at the parent member.
        total_value: The value to take when the drill up went above the top level of the hierarchy.

    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Year", "Month", "Day", "Shop", "Quantity", "Other"],
        ...     data=[
        ...         (2019, 7, 1, "Shop1", 15, 245),
        ...         (2019, 7, 2, "Shop1", 20, 505),
        ...         (2019, 6, 1, "Shop2", 25, 115),
        ...         (2019, 6, 2, "Shop2", 15, 135),
        ...         (2018, 7, 1, "Shop1", 5, 55),
        ...         (2018, 7, 2, "Shop2", 10, 145),
        ...         (2018, 6, 1, "Shop1", 15, 145),
        ...         (2018, 6, 2, "Shop2", 5, 155),
        ...     ],
        ... )
        >>> table = session.read_pandas(
        ...     df,
        ...     table_name="Parent Value",
        ... )
        >>> cube = session.create_cube(table)
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> h["Date"] = [table["Year"], table["Month"], table["Day"]]
        >>> m["Degree 1"] = tt.parent_value(m["Quantity.SUM"], degrees={h["Date"]: 1})
        >>> m["Degree 2"] = tt.parent_value(m["Quantity.SUM"], degrees={h["Date"]: 2})
        >>> m["Degree 2 with Quantity total"] = tt.parent_value(
        ...     m["Quantity.SUM"],
        ...     degrees={h["Date"]: 2},
        ...     total_value=m["Quantity.SUM"],
        ... )
        >>> m["Degree 2 with Other total"] = tt.parent_value(
        ...     m["Quantity.SUM"],
        ...     degrees={h["Date"]: 2},
        ...     total_value=m["Other.SUM"],
        ... )
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Other.SUM"],
        ...     m["Degree 1"],
        ...     m["Degree 2"],
        ...     m["Degree 2 with Quantity total"],
        ...     m["Degree 2 with Other total"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ... )
                        Quantity.SUM Other.SUM Degree 1 Degree 2 Degree 2 with Quantity total Degree 2 with Other total
        Year  Month Day
        Total                    110     1,500                                            110                     1,500
        2018                      35       500      110                                   110                     1,500
              6                   20       300       35      110                          110                       110
                    1             15       145       20       35                           35                        35
                    2              5       155       20       35                           35                        35
              7                   15       200       35      110                          110                       110
                    1              5        55       15       35                           35                        35
                    2             10       145       15       35                           35                        35
        2019                      75     1,000      110                                   110                     1,500
              6                   40       250       75      110                          110                       110
                    1             25       115       40       75                           75                        75
                    2             15       135       40       75                           75                        75
              7                   35       750       75      110                          110                       110
                    1             15       245       35       75                           75                        75
                    2             20       505       35       75                           75                        75
        >>> h["Date"].slicing = True
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Other.SUM"],
        ...     m["Degree 1"],
        ...     m["Degree 2"],
        ...     m["Degree 2 with Quantity total"],
        ...     m["Degree 2 with Other total"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ... )
                       Quantity.SUM Other.SUM Degree 1 Degree 2 Degree 2 with Quantity total Degree 2 with Other total
        Year Month Day
        2018 6     1             15       145       20       35                           35                        35
                   2              5       155       20       35                           35                        35
             7     1              5        55       15       35                           35                        35
                   2             10       145       15       35                           35                        35
        2019 6     1             25       115       40       75                           75                        75
                   2             15       135       40       75                           75                        75
             7     1             15       245       35       75                           75                        75
                   2             20       505       35       75                           75                        75
        >>> h["Date"].slicing = False
        >>> m["Degree 1 with applied filter"] = tt.parent_value(
        ...     m["Quantity.SUM"], degrees={h["Date"]: 1}, apply_filters=True
        ... )
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Degree 1"],
        ...     m["Degree 1 with applied filter"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ...     condition=l["Year"] == "2018",
        ... )
                        Quantity.SUM Degree 1 Degree 1 with applied filter
        Year  Month Day
        Total                     35
        2018                      35      110                           35
              6                   20       35                           35
                    1             15       20                           20
                    2              5       20                           20
              7                   15       35                           35
                    1              5       15                           15
                    2             10       15                           15
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Degree 1"],
        ...     m["Degree 1 with applied filter"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ...     condition=l["Shop"] == "Shop1",
        ... )
                        Quantity.SUM Degree 1 Degree 1 with applied filter
        Year  Month Day
        Total                     55
        2018                      20       55                           55
              6                   15       20                           20
                    1             15       15                           15
              7                    5       20                           20
                    1              5        5                            5
        2019                      35       55                           55
              7                   35       35                           35
                    1             15       35                           35
                    2             20       35                           35

    See Also:
        :func:`~atoti.total` to take the value at the top level member on each given hierarchy.

    """
    return ParentValue(
        measure,
        degrees,
        total_value,
        apply_filters,
    )


def total(measure: MeasureDescription, *hierarchies: Hierarchy) -> MeasureDescription:
    """Return a measure equal to the passed measure at the top level member on each given hierarchy.

    It ignores the filters on this hierarchy.

    If the hierarchy is not slicing, total is equal to the value for all the members.
    If the hierarchy is slicing, total is equal to the value on the first level.

    Args:
        measure: The measure to take the total of.
        hierarchies: The hierarchies on which to find the top-level member.


    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Year", "Month", "Day", "Price"],
        ...     data=[
        ...         (2019, 7, 1, 15.0),
        ...         (2019, 7, 2, 20.0),
        ...         (2019, 6, 1, 25.0),
        ...         (2019, 6, 2, 15.0),
        ...         (2018, 7, 1, 5.0),
        ...         (2018, 7, 2, 10.0),
        ...         (2018, 6, 1, 15.0),
        ...         (2018, 6, 2, 5.0),
        ...     ],
        ... )
        >>> table = session.read_pandas(
        ...     df,
        ...     table_name="Total",
        ... )
        >>> cube = session.create_cube(table)
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> h["Date"] = [table["Year"], table["Month"], table["Day"]]
        >>> m["Total(Price)"] = tt.total(m["Price.SUM"], h["Date"])
        >>> cube.query(
        ...     m["Price.SUM"],
        ...     m["Total(Price)"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ... )
                        Price.SUM Total(Price)
        Year  Month Day
        Total              110.00       110.00
        2018                35.00       110.00
              6             20.00       110.00
                    1       15.00       110.00
                    2        5.00       110.00
              7             15.00       110.00
                    1        5.00       110.00
                    2       10.00       110.00
        2019                75.00       110.00
              6             40.00       110.00
                    1       25.00       110.00
                    2       15.00       110.00
              7             35.00       110.00
                    1       15.00       110.00
                    2       20.00       110.00
        >>> h["Date"].slicing = True
        >>> cube.query(
        ...     m["Price.SUM"],
        ...     m["Total(Price)"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ... )
                       Price.SUM Total(Price)
        Year Month Day
        2018 6     1       15.00        35.00
                   2        5.00        35.00
             7     1        5.00        35.00
                   2       10.00        35.00
        2019 6     1       25.00        75.00
                   2       15.00        75.00
             7     1       15.00        75.00
                   2       20.00        75.00

    """
    return ParentValue(
        measure,
        {hierarchy: JAVA_MAX_INT for hierarchy in hierarchies},
        measure,
        False,
    )


def shift(
    measure: MeasureDescription, on: Level, *, offset: int = 1
) -> MeasureDescription:
    """Return a measure equal to the passed measure shifted to another member.

    Args:
        measure: The measure to shift.
        on: The level to shift on.
        offset: The amount of members to shift by.

    """
    return GenericMeasure("LEAD_LAG", measure, on._hierarchy, offset)


@dataclass(eq=False)
class FirstLast(MeasureDescription):
    """Shift the value."""

    _underlying_measure: MeasureDescription
    _level: Level
    _mode: Literal["FIRST", "LAST"]

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        underlying_name = get_measure_name(
            java_api=java_api, measure=self._underlying_measure, cube=cube
        )
        distilled_name = java_api.create_measure(
            cube,
            measure_name,
            "FIRST_LAST",
            underlying_name,
            self._level,
            self._mode,
        )
        return distilled_name


def _first(measure: MeasureDescription, on: Level) -> MeasureDescription:  # type: ignore
    """Return a measure equal to the first value of the passed measure on the level.

    Example:
        MeasureDescription definition::

            m["Turnover first day"] = atoti.first(m["Turnover"], on=l["Date"])

        Considering a single-level hierarchy ``Date``:

        +------------+----------+--------------------+
        |    Date    | Turnover | Turnover first day |
        +============+==========+====================+
        | 2020-01-01 |      100 |                100 |
        +------------+----------+--------------------+
        | 2020-01-02 |      500 |                100 |
        +------------+----------+--------------------+
        | 2020-01-03 |      200 |                100 |
        +------------+----------+--------------------+
        | 2020-01-04 |      400 |                100 |
        +------------+----------+--------------------+
        | 2020-01-05 |      300 |                100 |
        +------------+----------+--------------------+
        | TOTAL      |     1500 |                100 |
        +------------+----------+--------------------+

    Args:
        measure: The measure to shift.
        on: The level to shift on.

    """
    return FirstLast(measure, on, "FIRST")


def _last(measure: MeasureDescription, on: Level) -> MeasureDescription:  # type: ignore
    """Return a measure equal to the last value of the passed measure on the level.

    Example:
        Measure definition::

            m["Turnover last day"] = atoti.last(m["Turnover"], on=l["Date"])

        Considering a single-level hierarchy ``Date``:

        +------------+----------+-------------------+
        |    Date    | Turnover | Turnover last day |
        +============+==========+===================+
        | 2020-01-01 |      100 |               300 |
        +------------+----------+-------------------+
        | 2020-01-02 |      500 |               300 |
        +------------+----------+-------------------+
        | 2020-01-03 |      200 |               300 |
        +------------+----------+-------------------+
        | 2020-01-04 |      400 |               300 |
        +------------+----------+-------------------+
        | 2020-01-05 |      300 |               300 |
        +------------+----------+-------------------+
        | TOTAL      |     1500 |               300 |
        +------------+----------+-------------------+

    Args:
        measure: The measure to shift.
        on: The level to shift on.

    """
    return FirstLast(measure, on, "LAST")


@dataclass(eq=False)
class DateShift(MeasureDescription):
    """Shift the value."""

    _underlying_measure: MeasureDescription
    _hierarchy_name: str
    _shift: str
    _method: str

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        underlying_name = get_measure_name(
            java_api=java_api, measure=self._underlying_measure, cube=cube
        )
        levels = cube.hierarchies[self._hierarchy_name].levels
        level = list(levels.values())[-1]
        distilled_name = java_api.create_measure(
            cube,
            measure_name,
            "DATE_SHIFT",
            underlying_name,
            level,
            self._shift,
            self._method,
        )
        return distilled_name


_DateShiftMethod = Literal[  # pylint: disable=invalid-name
    "exact", "previous", "next", "interpolate"
]


def date_shift(  # pylint: disable=invalid-name
    measure: MeasureDescription,
    on: Hierarchy,
    *,
    offset: str,
    method: _DateShiftMethod = "exact",
) -> MeasureDescription:
    """Return a measure equal to the passed measure shifted to another date.

    Args:
        measure: The measure to shift.
        on: The hierarchy to shift on.
            Only hierarchies with a single level of type date (or datetime) are supported.
            If one of the member of the hierarchy is ``N/A`` their shifted value will always be ``None``.
        offset: The offset of the form ``xxDxxWxxMxxQxxY`` to shift by.
            Only the ``D``, ``W``, ``M``, ``Q``, and ``Y`` offset aliases are supported.
            Offset aliases have the `same meaning as Pandas' <https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases>`__.
        method: Determine the value to use when there is no member at the shifted date:

            * ``exact``: ``None``.
            * ``previous``: Value at the previous existing date.
            * ``next``: Value at the next existing date.
            * ``interpolate``: Linear interpolation of the values at the previous and next existing dates:

    Example:
        >>> from datetime import date
        >>> df = pd.DataFrame(
        ...     columns=["Date", "Price"],
        ...     data=[
        ...         (date(2020, 1, 5), 15.0),
        ...         (date(2020, 2, 3), 10.0),
        ...         (date(2020, 3, 3), 21.0),
        ...         (date(2020, 4, 5), 9.0),
        ...     ],
        ... )
        >>> table = session.read_pandas(
        ...     df,
        ...     table_name="date_shift example",
        ... )
        >>> cube = session.create_cube(table)
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> m["Exact"] = tt.date_shift(
        ...     m["Price.SUM"], on=h["Date"], offset="1M", method="exact"
        ... )
        >>> m["Previous"] = tt.date_shift(
        ...     m["Price.SUM"], on=h["Date"], offset="1M", method="previous"
        ... )
        >>> m["Next"] = tt.date_shift(
        ...     m["Price.SUM"], on=h["Date"], offset="1M", method="next"
        ... )
        >>> m["Interpolate"] = tt.date_shift(
        ...     m["Price.SUM"], on=h["Date"], offset="1M", method="interpolate"
        ... )
        >>> cube.query(
        ...     m["Price.SUM"],
        ...     m["Exact"],
        ...     m["Previous"],
        ...     m["Next"],
        ...     m["Interpolate"],
        ...     levels=[l["Date"]],
        ... )
                   Price.SUM  Exact Previous   Next Interpolate
        Date
        2020-01-05     15.00           10.00  21.00       10.76
        2020-02-03     10.00  21.00    21.00  21.00       21.00
        2020-03-03     21.00           21.00   9.00        9.73
        2020-04-05      9.00            9.00

        Explanations for :guilabel:`Interpolate`'s values:

        * ``10.76``: linear interpolation of ``2020-02-03``'s ``10`` and ``2020-03-03``'s ``21`` at ``2020-02-05``.
        * ``21.00``: no interpolation required since there is an exact match at ``2000-03-03``.
        * ``9.73``: linear interpolation of ``2020-03-03``'s ``21`` and ``2020-04-05``'s ``9`` for ``2020-04-03``.
        * ∅: no interpolation possible because there are no records after ``2020-04-05``.

    """
    if len(on.levels) > 1 or not is_temporal(next(iter(on.levels.values())).data_type):
        raise ValueError(
            f"Invalid hierarchy {on.name}, "
            "only hierarchies with a single date level are supported."
        )
    return DateShift(measure, on.name, offset, method)


def _unwrap_conditions(
    conditions: Mapping[Level, Any]
) -> Tuple[List[Any], List[Any], List[Any]]:
    """Unwrap a map of conditions.

    Transform a map of conditions into its corresponding list of levels, values, and target levels.
    """
    levels = []
    values = []
    target_levels = []
    for level, value in conditions.items():
        levels.append(level)
        if isinstance(value, Level):
            target_levels.append(value)
            values.append(None)
        else:
            target_levels.append(None)
            values.append(value)
    return levels, values, target_levels


def at(
    measure: MeasureDescription, coordinates: Mapping[Level, Any]
) -> MeasureDescription:
    """Return a measure equal to the passed measure at some other coordinates of the cube.

    Args:
        measure: The measure to take at other coordinates.
        coordinates: A ``{level_to_shift_on: value_to_shift_to}`` mapping.

                .. doctest::

                    >>> df = pd.DataFrame(
                    ...     columns=[
                    ...         "Country",
                    ...         "City",
                    ...         "Target Country",
                    ...         "Target City",
                    ...         "Quantity",
                    ...     ],
                    ...     data=[
                    ...         ("Germany", "Berlin", "UK", "London", 15),
                    ...         ("UK", "London", "Germany", "Berlin", 24),
                    ...         ("USA", "New York", "UK", "London", 10),
                    ...         ("USA", "New York", "France", "Paris", 3),
                    ...         ("USA", "Seattle", "Germany", "Berlin", 3),
                    ...     ],
                    ... )
                    >>> table = session.read_pandas(
                    ...     df, table_name="At", hierarchized_columns=[]
                    ... )
                    >>> cube = session.create_cube(table)
                    >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
                    >>> h["Geography"] = [table["Country"], table["City"]]
                    >>> h["Target Geography"] = [
                    ...     table["Target Country"],
                    ...     table["Target City"],
                    ... ]
                    >>> # Using a constant matching an existing member of the key level
                    >>> m["USA quantity"] = tt.at(
                    ...     m["Quantity.SUM"], {l["Country"]: "USA"}
                    ... )
                    >>> cube.query(
                    ...     m["Quantity.SUM"],
                    ...     m["USA quantity"],
                    ...     levels=[l["Country"]],
                    ... )
                            Quantity.SUM USA quantity
                    Country
                    Germany           15           16
                    UK                24           16
                    USA               16           16
                    >>> # Using another level whose current member the key level will be shifted to
                    >>> m["Target quantity"] = tt.at(
                    ...     m["Quantity.SUM"],
                    ...     {
                    ...         l["Country"]: l["Target Country"],
                    ...         l["City"]: l["Target City"],
                    ...     },
                    ... )
                    >>> cube.query(
                    ...     m["Quantity.SUM"],
                    ...     m["Target quantity"],
                    ...     levels=[l["City"], l["Target City"]],
                    ... )
                                                                Quantity.SUM Target quantity
                    Country City     Target Country Target City
                    Germany Berlin   UK             London                15              24
                    UK      London   Germany        Berlin                24              15
                    USA     New York France         Paris                  3
                                     UK             London                10              24
                            Seattle  Germany        Berlin                 3              15

              If this other level is not expressed, the shifting will not be done.

    """
    levels, values, target_levels = _unwrap_conditions(coordinates)
    return GenericMeasure("LEVEL_AT", measure, levels, values, target_levels)
