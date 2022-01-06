from __future__ import annotations

from typing import Iterable, Optional, Union, overload

from typeguard import check_argument_types, typeguard_ignore

from .._hierarchy_isin_conditions import HierarchyIsInCondition
from .._level_conditions import LevelCondition
from .._level_isin_conditions import LevelIsInCondition
from .._measures.boolean_measure import BooleanMeasure
from .._measures.filtered_measure import LevelValueFilteredMeasure, WhereMeasure
from .._measures.generic_measure import GenericMeasure
from .._measures.table_measure import SingleValueTableMeasure
from .._multi_condition import MultiCondition
from .._operation import ConditionOperation, Operation, TernaryOperation, _to_operation
from .._type_utils import DataTypeError
from ..column import Column
from ..hierarchy import Hierarchy
from ..level import Level
from ..measure import Measure
from ..measure_description import (
    LiteralMeasureValue,
    MeasureDescription,
    MeasureLike,
    _convert_to_measure_description,
)
from ..type import BOOLEAN, NULLABLE_BOOLEAN

OperationLike = Union[LiteralMeasureValue, Column, Operation]


def value(
    column: Column, *, levels: Optional[Iterable[Level]] = None
) -> MeasureDescription:
    """Return a measure equal to the value of the given table column.

    Args:
        column: The table column to get the value from.
        levels: The levels that must be expressed for this measure to possibly be non-null.

            When ``None``, the measure will also be ``None`` if the levels corresponding to the keys of *column*'s table are not expressed.

            Passing an empty collection propagate the value on all levels when possible.

    Example:
        >>> sales_df = pd.DataFrame(
        ...     columns=["Month", "City", "Product"],
        ...     data=[
        ...         ("January", "Manchester", "Ice cream"),
        ...         ("January", "London", "Ice cream"),
        ...         ("January", "London", "Burger"),
        ...         ("March", "New York", "Ice cream"),
        ...         ("March", "New York", "Burger"),
        ...     ],
        ... )
        >>> products_df = pd.DataFrame(
        ...     columns=["Name", "Month", "Purchase price"],
        ...     data=[
        ...         ("Ice cream", "January", 10.0),
        ...         ("Ice cream", "February", 10.0),
        ...         ("Ice cream", "March", 10.0),
        ...         ("Burger", "January", 10.0),
        ...         ("Burger", "February", 10.0),
        ...         ("Burger", "March", 8.0),
        ...     ],
        ... )
        >>> sales_table = session.read_pandas(
        ...     sales_df, keys=["Month", "City", "Product"], table_name="Sales"
        ... )
        >>> products_table = session.read_pandas(
        ...     products_df, keys=["Name", "Month"], table_name="Products"
        ... )
        >>> sales_table.join(
        ...     products_table, mapping={"Month": "Month", "Product": "Name"}
        ... )
        >>> cube = session.create_cube(sales_table)
        >>> l, m = cube.levels, cube.measures
        >>> m["Purchase price"] = tt.value(products_table["Purchase price"])

        By default, the values do not propagate:

        >>> cube.query(
        ...     m["Purchase price"],
        ...     m["contributors.COUNT"],
        ...     include_totals=True,
        ...     levels=[l["Month"], l["City"], l["Product"]],
        ... )
                                     Purchase price contributors.COUNT
        Month   City       Product
        Total                                                        5
        January                                                      3
                London                                               2
                           Burger             10.00                  1
                           Ice cream          10.00                  1
                Manchester                                           1
                           Ice cream          10.00                  1
        March                                                        2
                New York                                             2
                           Burger              8.00                  1
                           Ice cream          10.00                  1

        To propagate the values to the :guilabel:`City` level, the measure can instead be defined as follows:

        >>> m["Purchase price"] = tt.value(
        ...     products_table["Purchase price"], levels=[l["City"]]
        ... )

        With this definition, if all products of a city share the same purchase price, then the city inherits that price:

        >>> cube.query(
        ...     m["Purchase price"],
        ...     m["contributors.COUNT"],
        ...     include_totals=True,
        ...     levels=[l["Month"], l["City"], l["Product"]],
        ... )
                                     Purchase price contributors.COUNT
        Month   City       Product
        Total                                                        5
        January                                                      3
                London                        10.00                  2
                           Burger             10.00                  1
                           Ice cream          10.00                  1
                Manchester                    10.00                  1
                           Ice cream          10.00                  1
        March                                                        2
                New York                                             2
                           Burger              8.00                  1
                           Ice cream          10.00                  1

        Since the measure has not been defined to propagate on :guilabel:`Product`, changing the order of the levels prevents any propagation:

        >>> cube.query(
        ...     m["Purchase price"],
        ...     m["contributors.COUNT"],
        ...     include_totals=True,
        ...     levels=[l["Month"], l["Product"], l["City"]],
        ... )
                                     Purchase price contributors.COUNT
        Month   Product   City
        Total                                                        5
        January                                                      3
                Burger                                               1
                          London              10.00                  1
                Ice cream                                            2
                          London              10.00                  1
                          Manchester          10.00                  1
        March                                                        2
                Burger                                               1
                          New York             8.00                  1
                Ice cream                                            1
                          New York            10.00                  1

        Using ``levels=[]``, the value propagates to :guilabel:`Month` too:

        >>> m["Purchase price"] = tt.value(products_table["Purchase price"], levels=[])
        >>> cube.query(
        ...     m["Purchase price"],
        ...     m["contributors.COUNT"],
        ...     include_totals=True,
        ...     levels=[l["Month"], l["City"], l["Product"]],
        ... )
                                     Purchase price contributors.COUNT
        Month   City       Product
        Total                                                        5
        January                               10.00                  3
                London                        10.00                  2
                           Burger             10.00                  1
                           Ice cream          10.00                  1
                Manchester                    10.00                  1
                           Ice cream          10.00                  1
        March                                                        2
                New York                                             2
                           Burger              8.00                  1
                           Ice cream          10.00                  1

        When filtering out the members with a different :guilabel:`Product Price`, it even propagates all the way to the grand total:

        >>> cube.query(
        ...     m["Purchase price"],
        ...     m["contributors.COUNT"],
        ...     condition=l["Month"] == "January",
        ...     include_totals=True,
        ...     levels=[l["Month"], l["City"], l["Product"]],
        ... )
                                     Purchase price contributors.COUNT
        Month   City       Product
        Total                                 10.00                  3
        January                               10.00                  3
                London                        10.00                  2
                           Burger             10.00                  1
                           Ice cream          10.00                  1
                Manchester                    10.00                  1
                           Ice cream          10.00                  1

    """
    return SingleValueTableMeasure(column, levels)


@typeguard_ignore  # type checking is performed within the function
def filter(  # pylint: disable=redefined-builtin
    measure: MeasureLike,
    condition: Union[
        LevelCondition, MultiCondition, LevelIsInCondition, HierarchyIsInCondition
    ],
) -> MeasureDescription:
    """Return a filtered measure.

    The new measure is equal to the passed one where the condition is ``True`` and to ``None`` elsewhere.

    Example:

        >>> from datetime import date
        >>> data = pd.DataFrame(
        ...     {
        ...         "Date": [date(2021, 1, 13), date(2021, 7, 5), date(2021, 7, 6)],
        ...         "City": ["Paris", "Paris", "London"],
        ...         "Age": [18, 25, 8],
        ...         "Quantity": [200, 500, 100],
        ...     }
        ... )
        >>> table = session.read_pandas(
        ...     data,
        ...     table_name="City date table",
        ...     hierarchized_columns=["Date", "City", "Age"],
        ... )
        >>> table.head()
                Date    City  Age  Quantity
        0 2021-01-13   Paris   18       200
        1 2021-07-05   Paris   25       500
        2 2021-07-06  London    8       100
        >>> cube = session.create_cube(table)
        >>> l, m = cube.levels, cube.measures
        >>> # Levels compared to literals of the same type:
        >>> m["London Quantity.SUM"] = tt.filter(
        ...     m["Quantity.SUM"], l["City"] == "London"
        ... )
        >>> m["Quantity.SUM before July"] = tt.filter(
        ...     m["Quantity.SUM"], l["Date"] < date(2021, 7, 1)
        ... )
        >>> m["Quantity.SUM for age under 18"] = tt.filter(
        ...     m["Quantity.SUM"], l["Age"] <= 18
        ... )
        >>> # A conjunction of conditions using the ``&`` operator:
        >>> m["July Quantity.SUM in Paris"] = tt.filter(
        ...     m["Quantity.SUM"],
        ...     (
        ...         (l["City"] == "Paris")
        ...         & ((l["Date"]) >= date(2021, 7, 1))
        ...         & (l["Date"] <= date(2021, 7, 31))
        ...     ),
        ... )
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["London Quantity.SUM"],
        ...     m["Quantity.SUM before July"],
        ...     m["Quantity.SUM for age under 18"],
        ...     m["July Quantity.SUM in Paris"],
        ... )
          Quantity.SUM London Quantity.SUM Quantity.SUM before July Quantity.SUM for age under 18 July Quantity.SUM in Paris
        0          800                 100                      200                           300                        500
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["London Quantity.SUM"],
        ...     m["Quantity.SUM before July"],
        ...     m["Quantity.SUM for age under 18"],
        ...     m["July Quantity.SUM in Paris"],
        ...     levels=[l["Date"], l["Age"], l["City"]],
        ... )
                              Quantity.SUM London Quantity.SUM Quantity.SUM before July Quantity.SUM for age under 18 July Quantity.SUM in Paris
        Date       Age City
        2021-01-13 18  Paris           200                                          200                           200
        2021-07-05 25  Paris           500                                                                                                   500
        2021-07-06 8   London          100                 100                                                    100

    Args:
        measure: The measure to filter.
        condition: The condition to evaluate.

    """
    measure = _convert_to_measure_description(measure)
    if isinstance(condition, BooleanMeasure):
        raise ValueError("Use atoti.where() for conditions with measures.")

    if isinstance(condition, LevelCondition):
        if isinstance(condition._value, Level):
            raise ValueError("Conditions between two levels are not supported.")

        return LevelValueFilteredMeasure(measure, _level_conditions=[condition])

    if isinstance(condition, LevelIsInCondition):
        return LevelValueFilteredMeasure(measure, _level_isin_conditions=[condition])

    if isinstance(condition, HierarchyIsInCondition):
        return LevelValueFilteredMeasure(
            measure, _hierarchy_isin_conditions=[condition]
        )

    # Perform type checking after manual validation.
    check_argument_types()

    # We only allow the use of level conditions
    if condition._measure_conditions:
        raise ValueError("Use atoti.where() for conditions with measures.")

    return LevelValueFilteredMeasure(
        measure,
        condition._level_conditions,
        condition._level_isin_conditions,
        condition._hierarchy_isin_condition,
    )


@overload
def where(  # pylint: disable=too-many-positional-parameters
    condition: ConditionOperation,
    true_value: OperationLike,
    false_value: Optional[OperationLike] = None,
) -> TernaryOperation:
    ...


@overload
def where(  # pylint: disable=too-many-positional-parameters
    condition: Union[
        BooleanMeasure,
        LevelCondition,
        MultiCondition,
        HierarchyIsInCondition,
        LevelIsInCondition,
        Measure,
    ],
    true_value: MeasureLike,
    false_value: Optional[MeasureLike] = None,
) -> MeasureDescription:
    ...


def where(  # pylint: disable=too-many-positional-parameters
    condition: Union[
        BooleanMeasure,
        ConditionOperation,
        LevelCondition,
        MultiCondition,
        HierarchyIsInCondition,
        LevelIsInCondition,
        Measure,
    ],
    true_value: Union[MeasureLike, OperationLike],
    # Not keyword-only to be symmetrical with true_value and because
    # there probably will not be more optional parameters.
    false_value: Optional[Union[MeasureLike, OperationLike]] = None,
) -> Union[MeasureDescription, TernaryOperation]:
    """Return a conditional measure.

    This function is like an *if-then-else* statement:

    * Where the condition is ``True``, the new measure will be equal to ``true_value``.
    * Where the condition is ``False``, the new measure will be equal to ``false_value``.

    If one of the values compared in the condition is ``None``, the condition will be considered ``False``.

    Different types of conditions are supported:

    * Measures compared to anything measure-like::

        m["Test"] == 20

    * Levels compared to levels, (if the level is not expressed, it is considered ``None``)::

        l["source"] == l["destination"]

    * Levels compared to literals of the same type::

        l["city"] == "Paris"
        l["date"] > datetime.date(2020,1,1)
        l["age"] <= 18

    * A conjunction or disjunction of conditions using the ``&`` operator or ``|`` operator::

        (m["Test"] == 20) & (l["city"] == "Paris")
        (l["Country"] == "USA") | (l["Currency"] == "USD")

    Args:
        condition: The condition to evaluate.
        true_value: The measure to propagate where the condition is ``True``.
        false_value: The measure to propagate where the condition is ``False``.

    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Id", "City", "Value"],
        ...     data=[
        ...         (0, "Paris", 1.0),
        ...         (1, "Paris", 2.0),
        ...         (2, "London", 3.0),
        ...         (3, "London", 4.0),
        ...         (4, "Paris", 5.0),
        ...     ],
        ... )
        >>> table = session.read_pandas(df, keys=["Id"], table_name="filter example")
        >>> cube = session.create_cube(table)
        >>> l, m = cube.levels, cube.measures
        >>> m["Paris value"] = tt.where(l["City"] == "Paris", m["Value.SUM"], 0)
        >>> cube.query(m["Paris value"], levels=[l["City"]])
               Paris value
        City
        London         .00
        Paris         8.00

    """

    if isinstance(condition, ConditionOperation):
        true_operation = _to_operation(true_value)
        false_operation = _to_operation(false_value)
        return TernaryOperation(
            condition=condition,
            true_operation=true_operation,
            false_operation=false_operation,
        )

    if isinstance(true_value, (Column, Operation)) or isinstance(
        false_value, (Column, Operation)
    ):
        raise ValueError(
            "Cannot use tt.where on operations if the condition is not also an operation. Please convert the true (and false) value(s) to a measure(s)."
        )

    # Collect the measure conditions.
    measure_conditions = []

    if isinstance(condition, BooleanMeasure):
        measure_conditions.append(condition)

    elif isinstance(
        condition, (LevelCondition, HierarchyIsInCondition, LevelIsInCondition)
    ):
        measure_conditions.append(condition._to_measure_description())

    elif isinstance(condition, Measure):
        if condition.data_type in [
            BOOLEAN,
            NULLABLE_BOOLEAN,
        ]:
            measure_conditions.append(condition)
        else:
            raise DataTypeError(condition, "boolean")

    else:
        # condition._... is empty nothing happen
        measure_conditions.extend(
            [
                level_condition._to_measure_description()
                for level_condition in condition._level_conditions
            ]
            + [
                hierarchy_isin_condition._to_measure_description()
                for hierarchy_isin_condition in condition._hierarchy_isin_condition
            ]
            + [
                level_isin_condition._to_measure_description()
                for level_isin_condition in condition._level_isin_conditions
            ]
            + list(condition._measure_conditions)
        )

    return WhereMeasure(
        _convert_to_measure_description(true_value),
        _convert_to_measure_description(false_value)
        if false_value is not None
        else None,
        measure_conditions,
    )


def conjunction(*measures: BooleanMeasure) -> BooleanMeasure:
    """Return a measure equal to the logical conjunction of the passed measures."""
    return BooleanMeasure("and", measures)


def rank(
    measure: MeasureDescription,
    hierarchy: Hierarchy,
    *,
    ascending: bool = True,
    apply_filters: bool = True,
) -> MeasureDescription:
    """Return a measure equal to the rank of a hierarchy's members according to a reference measure.

    Members with equal values are further ranked using the level comparator.

    Args:
        measure: The measure on which the ranking is done.
        hierarchy: The hierarchy containing the members to rank.
        ascending: When set to ``False``, the 1st place goes to the member with greatest value.
        apply_filters: When ``True``, query filters will be applied before ranking members.
            When ``False``, query filters will be applied after the ranking, resulting in "holes" in the ranks.

    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Year", "Month", "Day", "Quantity"],
        ...     data=[
        ...         (2000, 1, 1, 15),
        ...         (2000, 1, 2, 10),
        ...         (2000, 2, 1, 30),
        ...         (2000, 2, 2, 20),
        ...         (2000, 2, 5, 30),
        ...         (2000, 4, 4, 5),
        ...         (2000, 4, 5, 10),
        ...         (2020, 12, 6, 15),
        ...         (2020, 12, 7, 15),
        ...     ],
        ... )
        >>> table = session.read_pandas(
        ...     df,
        ...     table_name="Rank",
        ... )
        >>> cube = session.create_cube(table)
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> h["Date"] = [table["Year"], table["Month"], table["Day"]]
        >>> m["Rank"] = tt.rank(m["Quantity.SUM"], h["Date"])
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Rank"],
        ...     levels=[l["Day"]],
        ...     include_totals=True,
        ... )
                        Quantity.SUM Rank
        Year  Month Day
        Total                    150    1
        2000                     120    2
              1                   25    2
                    1             15    2
                    2             10    1
              2                   80    3
                    1             30    2
                    2             20    1
                    5             30    3
              4                   15    1
                    4              5    1
                    5             10    2
        2020                      30    1
              12                  30    1
                    6             15    1
                    7             15    2
        >>> m["Rank with filters not applied"] = tt.rank(
        ...     m["Quantity.SUM"], h["Date"], apply_filters=False
        ... )
        >>> cube.query(
        ...     m["Quantity.SUM"],
        ...     m["Rank"],
        ...     m["Rank with filters not applied"],
        ...     levels=[l["Month"]],
        ...     include_totals=True,
        ...     condition=l["Year"] == "2000",
        ... )
                    Quantity.SUM Rank Rank with filters not applied
        Year  Month
        Total                120    1                             1
        2000                 120    1                             2
              1               25    2                             2
              2               80    3                             3
              4               15    1                             1

        :guilabel:`2000-01-01` and :guilabel:`2000-01-05` have the same :guilabel:`Quantity.SUM` value so `l["Day"]`'s comparator is used to rank them.
    """
    return GenericMeasure("RANK", measure, hierarchy, ascending, apply_filters)
