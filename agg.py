from __future__ import annotations

from typing import List, Optional, Union

from ._docs_utils import (
    QUANTILE_DOC,
    STD_AND_VAR_DOC,
    STD_DOC_KWARGS,
    VAR_DOC_KWARGS,
    doc,
)
from ._measures.calculated_measure import AggregatedMeasure
from ._measures.generic_measure import GenericMeasure
from ._measures.sum_product_measure import (
    SumProductEncapsulationMeasure,
    SumProductFieldsMeasure,
)
from ._measures.table_measure import TableMeasure
from ._operation import Operation
from ._type_utils import PercentileInterpolation, PercentileMode, VarianceMode
from .array import quantile as array_quantile
from .level import Level
from .math import sqrt
from .measure_description import MeasureConvertible, MeasureDescription
from .scope._utils import LeafLevels, Window
from .scope.scope import Scope
from .table import Column

MeasureOrMeasureConvertible = Union[MeasureDescription, MeasureConvertible]
ColumnOrOperation = Union[Column, Operation]


_BASIC_DOC = """Return a measure equal to the {value} of the passed measure across the specified scope.

    {args}

    Example:

        >>> df = pd.DataFrame(
        ...     columns=["id", "Quantity", "Price", "Other"],
        ...     data=[
        ...         ("a1", 100, 12.5, 1),
        ...         ("a2", 10, 43, 2),
        ...         ("a3", 1000, 25.9, 2),
        ...     ],
        ... )
        >>> table = session.read_pandas(
        ...     df,
        ...     table_name="Product",
        ...     keys=["id"],
        ... )
        >>> table.head()
            Quantity  Price  Other
        id
        a1       100   12.5      1
        a2        10   43.0      2
        a3      1000   25.9      2
        >>> cube = session.create_cube(table)
        >>> m = cube.measures
{example}

    .. doctest::
        :hide:

        >>> session._clear()
"""

_SCOPE_DOC = """
        scope: The scope of the aggregation.
               When ``None`` is specified, the natural aggregation scope is used: it contains all the data in the cube which coordinates match the ones of the currently evaluated member.
    """
_BASIC_ARGS_DOC = (
    """
    Args:
        operand: The measure or table column to aggregate.
"""
    + _SCOPE_DOC
)

_QUANTILE_STD_AND_VAR_DOC_KWARGS = {
    "what": "of the passed measure across the specified scope",
}


def _agg(
    agg_fun: str,
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    """Return a measure aggregating the passed one.

    A scope can only be specified when passing an instance of MeasureDescription.
    """
    from ._udaf import UserDefinedAggregateFunction

    if isinstance(operand, Operation):
        udaf = UserDefinedAggregateFunction(operand, agg_fun)
        udaf.register_aggregation_function()
        return GenericMeasure(
            "ATOTI_UDAF_MEASURE",
            udaf.column_names,
            udaf.plugin_key,
            scope.levels if isinstance(scope, LeafLevels) else [],
            agg_fun,
        )
    if not isinstance(operand, MeasureDescription):
        if scope is not None:
            raise ValueError(
                (
                    """Illegal argument "scope" if you are not passing a measure object """
                    """as "measure" argument."""
                )
            )
        if isinstance(operand, Column):
            return TableMeasure(operand, agg_fun, operand._table)
        return operand._to_measure_description(agg_fun)

    if isinstance(scope, Window):
        return scope._create_aggregated_measure(operand, agg_fun)
    if isinstance(scope, LeafLevels) or scope is None:
        return AggregatedMeasure(operand, agg_fun, scope)
    raise TypeError(f"Scope {scope} of invalid type {type(scope).__name__} passed")


def _count(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    """Return a measure equal to the number of aggregated elements.

    With a table column, it counts the number of facts.
    With a measure and a level, it counts the number of level members.
    To count the number of distinct elements, use :func:`atoti.agg.count_distinct`.
    """
    return _agg(agg_fun="COUNT", operand=operand, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="sum",
    example="""
        >>> m["Quantity.SUM"] = tt.agg.sum(table["Quantity"])
        >>> cube.query(m["Quantity.SUM"])
          Quantity.SUM
        0        1,110""".replace(
        "\n", "", 1
    ),
)
def sum(  # pylint: disable=redefined-builtin
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="SUM", operand=operand, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="product",
    example="""
        >>> m["Other.PROD"] = tt.agg.prod(table["Other"])
        >>> cube.query(m["Other.PROD"])
          Other.PROD
        0          4""".replace(
        "\n", "", 1
    ),
)
def prod(  # pylint: disable=redefined-builtin
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="MULTIPLY", operand=operand, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="mean",
    example="""
        >>> m["Quantity.MEAN"] = tt.agg.mean(table["Quantity"])
        >>> cube.query(m["Quantity.MEAN"])
          Quantity.MEAN
        0        370.00""".replace(
        "\n", "", 1
    ),
)
def mean(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="MEAN", operand=operand, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="minimum",
    example="""
        >>> m["Minimum Price"] = tt.agg.min(table["Price"])
        >>> cube.query(m["Minimum Price"])
          Minimum Price
        0         12.50""".replace(
        "\n", "", 1
    ),
)
def min(  # pylint: disable=redefined-builtin
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="MIN", operand=operand, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="maximum",
    example="""
        >>> m["Maximum Price"] = tt.agg.max(table["Price"])
        >>> cube.query(m["Maximum Price"])
          Maximum Price
        0         43.00""".replace(
        "\n", "", 1
    ),
)
def max(  # pylint: disable=redefined-builtin
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="MAX", operand=operand, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="median",
    example="""
        >>> m["Median Price"] = tt.agg.median(table["Price"])
        >>> cube.query(m["Median Price"])
          Median Price
        0        25.90""".replace(
        "\n", "", 1
    ),
)
def median(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return quantile(operand, q=0.5, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="sum of the square",
    example="""
        >>> m["Other.SQUARE_SUM"] = tt.agg.square_sum(table["Other"])
        >>> cube.query(m["Other.SQUARE_SUM"])
          Other.SQUARE_SUM
        0                9""".replace(
        "\n", "", 1
    ),
)
def square_sum(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="SQ_SUM", operand=operand, scope=scope)


@doc(
    STD_AND_VAR_DOC,
    _SCOPE_DOC,
    **{**VAR_DOC_KWARGS, **_QUANTILE_STD_AND_VAR_DOC_KWARGS},
)
def var(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    mode: VarianceMode = "sample",
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    size = _count(operand, scope=scope)
    mean_value = mean(operand, scope=scope)
    population_var = square_sum(operand, scope=scope) / size - mean_value * mean_value
    if mode == "population":
        return population_var
    # Apply Bessel's correction
    return population_var * size / (size - 1)


@doc(
    STD_AND_VAR_DOC,
    _SCOPE_DOC,
    **{**STD_DOC_KWARGS, **_QUANTILE_STD_AND_VAR_DOC_KWARGS},
)
def std(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    mode: VarianceMode = "sample",
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return sqrt(var(operand, mode=mode, scope=scope))


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="sum of the negative values",
    example="""
        >>> m["Quantity.SHORT"] = tt.agg.short(table["Quantity"])
        >>> cube.query(m["Quantity.SHORT"])
          Quantity.SHORT
        0              0""".replace(
        "\n", "", 1
    ),
)
def short(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="SHORT", operand=operand, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="sum of the positive values",
    example="""
        >>> m["Quantity.LONG"] = tt.agg.long(table["Quantity"])
        >>> cube.query(m["Quantity.LONG"])
          Quantity.LONG
        0         1,110""".replace(
        "\n", "", 1
    ),
)
def long(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="LONG", operand=operand, scope=scope)


@doc(
    _BASIC_DOC,
    args=_BASIC_ARGS_DOC,
    value="distinct count",
    example="""
        >>> m["Price.DISTINCT_COUNT"] = tt.agg.count_distinct(table["Price"])
        >>> cube.query(m["Price.DISTINCT_COUNT"])
          Price.DISTINCT_COUNT
        0                    3""".replace(
        "\n", "", 1
    ),
)
def count_distinct(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return _agg(agg_fun="DISTINCT_COUNT", operand=operand, scope=scope)


def _vector(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    """Return an array measure representing the values of the passed operand across the specified scope."""
    return _agg(agg_fun="VECTOR", operand=operand, scope=scope)


@doc(QUANTILE_DOC, _SCOPE_DOC, **_QUANTILE_STD_AND_VAR_DOC_KWARGS)
def quantile(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    q: Union[float, MeasureDescription],
    *,
    mode: PercentileMode = "inc",
    interpolation: PercentileInterpolation = "linear",
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    return array_quantile(
        _vector(operand, scope=scope), q=q, mode=mode, interpolation=interpolation
    )


_EXTREMUM_MEMBER_DOC = """Return a measure equal to the member {op}imizing the passed measure on the given level.

    When multiple members {op}imize the passed measure, the first one
    (according to the comparator of the given level) is returned.

    Args:
        measure: The measure to {op}imize.
        level: The level on which the {op}imizing member is searched for.

    Example:

        >>> df = pd.DataFrame(
        ...     columns=["Continent", "City", "Price"],
        ...     data=[
        ...         ("Europe", "Paris", 200.0),
        ...         ("Europe", "Berlin", 150.0),
        ...         ("Europe", "London", 240.0),
        ...         ("North America", "New York", 270.0),
        ...     ],
        ... )
        >>> table = session.read_pandas(
        ...     df,
        ...     table_name="City price table",
        ... )
        >>> table.head()
               Continent      City  Price
        0         Europe     Paris  200.0
        1         Europe    Berlin  150.0
        2         Europe    London  240.0
        3  North America  New York  270.0
        >>> cube = session.create_cube(table, mode="manual")
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> h["Geography"] = [table["Continent"], table["City"]]
        >>> m["Price"] = tt.value(table["Price"])
{example}


        .. doctest::
            :hide:

            >>> session._clear()
"""


@doc(
    _EXTREMUM_MEMBER_DOC,
    op="max",
    example="""
        >>> m["City with maximum price"] = tt.agg.max_member(m["Price"], l["City"])

        At the given level, the measure is equal to the current member of the City level:

        >>> cube.query(m["City with maximum price"], levels=[l["City"]])
                               City with maximum price
        Continent     City
        Europe        Berlin                    Berlin
                      London                    London
                      Paris                      Paris
        North America New York                New York

        At a level above it, the measure is equal to the city of each continent with the maximum price:

        >>> cube.query(m["City with maximum price"], levels=[l["Continent"]])
                      City with maximum price
        Continent
        Europe                         London
        North America                New York

        At the top level, the measure is equal to the city with the maximum price across all continents:

        >>> cube.query(m["City with maximum price"])
          City with maximum price
        0                New York""".replace(
        "\n", "", 1
    ),
)
def max_member(
    measure: MeasureOrMeasureConvertible, level: Level
) -> MeasureDescription:
    if not isinstance(measure, MeasureDescription):
        measure = measure._to_measure_description()
    return GenericMeasure("COMPARABLE_MAX", measure, level, True, False)


@doc(
    _EXTREMUM_MEMBER_DOC,
    op="min",
    example="""
        >>> m["City with minimum price"] = tt.agg.min_member(m["Price"], l["City"])

        At the given level, the measure is equal to the current member of the City level:

        >>> cube.query(m["City with minimum price"], levels=[l["City"]])
                               City with minimum price
        Continent     City
        Europe        Berlin                    Berlin
                      London                    London
                      Paris                      Paris
        North America New York                New York

        At a level above it, the measure is equal to the city of each continent with the minimum price:

        >>> cube.query(m["City with minimum price"], levels=[l["Continent"]])
                      City with minimum price
        Continent
        Europe                         Berlin
        North America                New York

        At the top level, the measure is equal to the city with the minimum price across all continents:

        >>> cube.query(m["City with minimum price"])
          City with minimum price
        0                  Berlin""".replace(
        "\n", "", 1
    ),
)
def min_member(
    measure: MeasureOrMeasureConvertible, level: Level
) -> MeasureDescription:
    if not isinstance(measure, MeasureDescription):
        measure = measure._to_measure_description()
    return GenericMeasure("COMPARABLE_MAX", measure, level, False, False)


@doc(scope=_SCOPE_DOC)
def sum_product(
    *factors: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    scope: Optional[Scope] = None,
) -> MeasureDescription:
    """Return a measure equal to the sum product aggregation of the passed factors across the specified scope.

    Args:
        factors: Column, Measure or Level to do the sum product of.
        {scope}

    Example:

        >>> from datetime import date
        >>> df = pd.DataFrame(
        ...     columns=["Date", "Category", "Price", "Quantity", "Array"],
        ...     data=[
        ...         (date(2020, 1, 1), "TV", 300.0, 5, [10.0, 15.0]),
        ...         (date(2020, 1, 2), "TV", 200.0, 1, [5.0, 15.0]),
        ...         (date(2020, 1, 1), "Computer", 900.0, 2, [2.0, 3.0]),
        ...         (date(2020, 1, 2), "Computer", 800.0, 3, [10.0, 20.0]),
        ...         (date(2020, 1, 1), "TV", 500.0, 2, [3.0, 10.0]),
        ...     ],
        ... )
        >>> table = session.read_pandas(
        ...     df,
        ...     table_name="Date",
        ... )
        >>> table.head()
                Date  Category  Price  Quantity         Array
        0 2020-01-01        TV  300.0         5  [10.0, 15.0]
        1 2020-01-02        TV  200.0         1   [5.0, 15.0]
        2 2020-01-01  Computer  900.0         2    [2.0, 3.0]
        3 2020-01-02  Computer  800.0         3  [10.0, 20.0]
        4 2020-01-01        TV  500.0         2   [3.0, 10.0]
        >>> cube = session.create_cube(table)
        >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
        >>> m["turnover"] = tt.agg.sum_product(table["Price"], table["Quantity"])
        >>> cube.query(m["turnover"], levels=[l["Category"]])
                  turnover
        Category
        Computer  4,200.00
        TV        2,700.00
        >>> m["array sum product"] = tt.agg.sum_product(table["Price"], table["Array"])
        >>> cube.query(m["array sum product"])
                       array sum product
        0  doubleVector[2]{{15300.0, ...}}
    """
    if len(factors) < 1:
        raise ValueError("At least one factor is needed")
    # pyright does not know there ris only columns in factors so we build a new sequence.
    factors_column: List[Column] = []
    for factor in factors:
        if isinstance(factor, Column):
            factors_column.append(factor)
    # Case with table fields
    if len(factors_column) == len(factors):
        if scope is None:
            return SumProductFieldsMeasure(factors_column)
        raise ValueError(
            "Scope is defined for table columns aggregation. "
            + "Scope must not be defined since this aggregation will be done at fact level."
        )
    # Otherwise case with two measures.
    return _agg(
        "SUM_PRODUCT",
        SumProductEncapsulationMeasure(
            [_get_factor_as_measure(factor) for factor in factors]
        ),
        scope=scope,
    )


def _get_factor_as_measure(
    factor: Union[ColumnOrOperation, MeasureOrMeasureConvertible]
) -> MeasureDescription:
    if isinstance(factor, MeasureDescription):
        return factor
    if isinstance(factor, (Column, Operation)):
        raise ValueError(
            "Cannot perform a sum_product aggregation on a combination of measures and table columns or operations. Convert all the factors to measures."
        )
    return factor._to_measure_description()
