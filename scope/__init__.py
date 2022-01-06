from typing import Optional, Tuple, Union

from atoti.hierarchy import Hierarchy
from atoti.level import Level

from .._type_utils import is_date
from ._utils import CumulativeTimeWindow, CumulativeWindow, LeafLevels, SiblingsWindow
from .scope import Scope


def cumulative(
    level: Level,
    *,
    dense: bool = False,
    partitioning: Optional[Level] = None,
    window: Optional[Union[range, Tuple[Optional[str], Optional[str]]]] = None,
) -> Scope:
    """Create a scope to be used in the computation of cumulative aggregations.

    Cumulative aggregations include cumulative sums (also called running sum or prefix sum), mean, min, max, etc.

    Args:
        level: The level along which the aggregation is performed.
        dense: When ``True``, all members of the level, even those with no value for the underlying measure, will be taken into account for the cumulative aggregation (resulting in repeating values).
        partitioning: The levels in the hierarchy at which to start the aggregation over.
        window: The custom aggregation window.
            The window defines the set of members before and after a given member (using the level comparator) to be considered in the computation of the cumulative aggregation.

            The window can be a:

            * ``range`` starting with a <=0 value and ending with a >=0 value.

               By default the window is ``range(-∞, 0)``, meaning that the value for a given member is computed using all of the members before it and none after it.

               For instance, to compute the sliding mean on the 5 previous members of a level::

                 m2 = atoti.agg.mean(m1, scope=tt.scope.cumulative(l["date"], window=range(-5, 0)))

            * time period as a two-element tuple starting with an offset of the form ``-xxDxxWxxMxxQxxY`` or ``None`` and ending with an offset of the form ``xxDxxWxxMxxQxxY`` or ``None``.

              For instance, to compute the 5 previous days sliding mean::

                m2 = atoti.agg.mean(m1, scope=tt.scope.cumulative(l["date"], window=("-5D", None)))

    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Year", "Month", "Day", "Quantity"],
        ...     data=[
        ...         (2019, 7, 1, 15),
        ...         (2019, 7, 2, 20),
        ...         (2019, 6, 1, 25),
        ...         (2019, 6, 2, 15),
        ...         (2018, 7, 1, 5),
        ...         (2018, 7, 2, 10),
        ...         (2018, 6, 1, 15),
        ...         (2018, 6, 2, 5),
        ...     ],
        ... )
        >>> table = session.read_pandas(df, table_name="Cumulative")
        >>> cube = session.create_cube(table)
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> h["Date"] = [table["Year"], table["Month"], table["Day"]]
        >>> m["Quantity.SUM"] = tt.agg.sum(table["Quantity"])
        >>> m["Cumulative quantity"] = tt.agg.sum(
        ...     m["Quantity.SUM"], scope=tt.scope.cumulative(l["Day"])
        ... )
        >>> m["Cumulative quantity partitioned by month"] = tt.agg.sum(
        ...     m["Quantity.SUM"],
        ...     scope=tt.scope.cumulative(l["Day"], partitioning=l["Month"]),
        ... )
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Cumulative quantity"],
        ...     m["Cumulative quantity partitioned by month"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ... )
                        Quantity.SUM Cumulative quantity Cumulative quantity partitioned by month
        Year  Month Day
        Total                    110                 110
        2018                      35                  35
              6                   20                  20                                       20
                    1             15                  15                                       15
                    2              5                  20                                       20
              7                   15                  35                                       15
                    1              5                  25                                        5
                    2             10                  35                                       15
        2019                      75                 110
              6                   40                  75                                       40
                    1             25                  60                                       25
                    2             15                  75                                       40
              7                   35                 110                                       35
                    1             15                  90                                       15
                    2             20                 110                                       35

    """
    if window is None:
        return CumulativeWindow(level, dense, window, partitioning)
    if isinstance(window, Tuple):
        if not is_date(level.data_type):
            raise ValueError("Time period window can only be used with date levels.")
        back = window[0]
        if back is not None and not back.startswith("-"):
            raise ValueError("back period parameter must be a negative time frame.")
        forward = window[1]
        if forward is not None and forward.startswith("-"):
            raise ValueError("forward period parameter must be a positive time frame")
        return CumulativeTimeWindow(level, window, partitioning)
    if window.step != 1:
        raise ValueError(
            "Running aggregation windows only support ranges with step of size 1."
        )
    if window.start > 0 or window.stop < 0:
        raise ValueError(
            "Running aggregation window should have a start value less than or equal to 0, "
            "and a stop value greater than or equal to 0."
        )
    return CumulativeWindow(level, dense, window, partitioning)


def siblings(hierarchy: Hierarchy, *, exclude_self: bool = False) -> Scope:
    """Create a "siblings" aggregation scope.

    In a siblings scope, the value for the member of a given level in the hierarchy is computed by taking the contribution of all of the members on the same level (its siblings).

    A siblings aggregation is an appropriate tool for operations such as marginal aggregations (marginal VaR, marginal mean) for non-linear aggregation functions.

    Args:
        hierarchy: The hierarchy containing the levels along which the aggregation is performed.
        exclude_self: Whether to include the current member's contribution in its cumulative value.

    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Year", "Month", "Day", "Quantity"],
        ...     data=[
        ...         (2019, 7, 1, 15),
        ...         (2019, 7, 2, 20),
        ...         (2019, 7, 3, 30),
        ...         (2019, 6, 1, 25),
        ...         (2019, 6, 2, 15),
        ...         (2018, 7, 1, 5),
        ...         (2018, 7, 2, 10),
        ...         (2018, 6, 1, 15),
        ...         (2018, 6, 2, 5),
        ...     ],
        ... )
        >>> table = session.read_pandas(df, table_name="Siblings")
        >>> cube = session.create_cube(table, mode="manual")
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> h["Date"] = [table["Year"], table["Month"], table["Day"]]
        >>> m["Quantity.SUM"] = tt.agg.sum(table["Quantity"])
        >>> m["Siblings quantity"] = tt.agg.sum(
        ...     m["Quantity.SUM"], scope=tt.scope.siblings(h["Date"])
        ... )
        >>> m["Siblings quantity excluding self"] = tt.agg.sum(
        ...     m["Quantity.SUM"], scope=tt.scope.siblings(h["Date"], exclude_self=True)
        ... )
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Siblings quantity"],
        ...     m["Siblings quantity excluding self"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ... )
                        Quantity.SUM Siblings quantity Siblings quantity excluding self
        Year  Month Day
        Total                    140               140                                0
        2018                      35               140                              105
              6                   20                35                               15
                    1             15                20                                5
                    2              5                20                               15
              7                   15                35                               20
                    1              5                15                               10
                    2             10                15                                5
        2019                     105               140                               35
              6                   40               105                               65
                    1             25                40                               15
                    2             15                40                               25
              7                   65               105                               40
                    1             15                65                               50
                    2             20                65                               45
                    3             30                65                               35
    """
    return SiblingsWindow(
        hierarchy,
        exclude_self,
    )


def origin(*levels: Level) -> Scope:
    """Create an aggregation scope with an arbitrary number of levels.

    The passed levels define a boundary above and under which the aggregation is performed differently.
    When those levels are not expressed in a query, the measure will drill down until finding the value for all members of these levels, and then aggregate those values using the user-defined aggregation function.
    This allows to compute measures that show the yearly mean when looking at the grand total, but the sum of each month's value when looking at each year individually.

    Args:
        levels: The levels defining the dynamic aggregation domain.

    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Year", "Month", "Day", "Quantity"],
        ...     data=[
        ...         (2019, 7, 1, 15),
        ...         (2019, 7, 2, 20),
        ...         (2019, 7, 3, 30),
        ...         (2019, 6, 1, 25),
        ...         (2019, 6, 2, 15),
        ...         (2018, 7, 1, 5),
        ...         (2018, 7, 2, 10),
        ...         (2018, 6, 1, 15),
        ...         (2018, 6, 2, 5),
        ...     ],
        ... )
        >>> table = session.read_pandas(df, table_name="Origin")
        >>> cube = session.create_cube(table, mode="manual")
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> h["Date"] = [table["Year"], table["Month"], table["Day"]]
        >>> m["Quantity.SUM"] = tt.agg.sum(table["Quantity"])
        >>> m["Average of monthly quantities"] = tt.agg.mean(
        ...     m["Quantity.SUM"], scope=tt.scope.origin(l["Month"])
        ... )
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Average of monthly quantities"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ... )
                        Quantity.SUM Average of monthly quantities
        Year  Month Day
        Total                    140                         35.00
        2018                      35                         17.50
              6                   20                         20.00
                    1             15                         15.00
                    2              5                          5.00
              7                   15                         15.00
                    1              5                          5.00
                    2             10                         10.00
        2019                     105                         52.50
              6                   40                         40.00
                    1             25                         25.00
                    2             15                         15.00
              7                   65                         65.00
                    1             15                         15.00
                    2             20                         20.00
                    3             30                         30.00
    """
    if len(levels) == 1 and isinstance(levels[0], list):
        raise TypeError("origin takes one or more levels, not a list.")

    return LeafLevels(list(levels))
