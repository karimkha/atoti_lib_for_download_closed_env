"""atoti is designed to handle array data efficiently.

There are multiple ways to load arrays into atoti tables.
For instance:

    * With :meth:`atoti.session.Session.read_pandas`:

        .. doctest:: array

            >>> import numpy as np
            >>> df = pd.DataFrame(
            ...     columns=["NumPy array", "Python list"],
            ...     data=[
            ...         (np.array([1.0, 2.0, 3.0]), [1, 2, 3]),
            ...         (np.array([4.0, 5.0, 6.0]), [4, 5, 6]),
            ...         (np.array([7.0, 8.0, 9.0]), [7, 8, 9]),
            ...     ],
            ... )
            >>> df
                   NumPy array Python list
            0  [1.0, 2.0, 3.0]   [1, 2, 3]
            1  [4.0, 5.0, 6.0]   [4, 5, 6]
            2  [7.0, 8.0, 9.0]   [7, 8, 9]

            >>> pandas_table = session.read_pandas(
            ...     df, table_name="DataFrame with arrays"
            ... )
            >>> pandas_table.head()
                   NumPy array Python list
            0  [1.0, 2.0, 3.0]   [1, 2, 3]
            1  [4.0, 5.0, 6.0]   [4, 5, 6]
            2  [7.0, 8.0, 9.0]   [7, 8, 9]

    * With :meth:`atoti.session.Session.read_csv`:

        .. doctest:: array

            >>> pnl_table = session.read_csv(
            ...     f"{RESOURCES}/pnl.csv",
            ...     array_separator=";",
            ...     keys=["Continent", "Country"],
            ...     table_name="PnL",
            ... )
            >>> pnl_table.head()
                                                                             PnL
            Continent Country
            Europe    France   [-0.465, -0.025, 0.601, 0.423, -0.815, 0.024, ...
                      UK       [11.449, -35.5464, -66.641, -48.498, -6.3126, ...
            America   Mexico   [-10.716, 9.593, 1.356, -21.185, 5.989, 9.686,...
            Asia      China    [-1.715, 2.425, -4.059, 4.102, -2.331, -2.662,...
                      India    [-18.716, 8.583, -41.356, -11.138, 3.949, 5.66...

As for scalar measures, atoti provides the default ``SUM`` and ``MEAN`` aggregations on array measures.
They are applied element by element:

.. doctest:: array

    >>> cube = session.create_cube(pnl_table)
    >>> l, m = cube.levels, cube.measures
    >>> cube.query(m["PnL.SUM"], m["PnL.MEAN"], levels=[l["Continent"]])
                                      PnL.SUM                         PnL.MEAN
    Continent
    America    doubleVector[10]{-10.716, ...}   doubleVector[10]{-10.716, ...}
    Asia       doubleVector[10]{-20.431, ...}  doubleVector[10]{-10.2155, ...}
    Europe      doubleVector[10]{10.984, ...}     doubleVector[10]{5.492, ...}

Besides the functions below, arrays support the following operations:

    * Arithmetic operators:

        .. doctest:: array

            >>> m["PnL +10"] = m["PnL.SUM"] + 10.0
            >>> cube.query(m["PnL +10"])
                                      PnL +10
            0  doubleVector[10]{-10.163, ...}

            >>> m["PnL -10"] = m["PnL.SUM"] - 10.0
            >>> cube.query(m["PnL -10"])
                                      PnL -10
            0  doubleVector[10]{-30.163, ...}

            >>> m["PnL x10"] = m["PnL.SUM"] * 10.0
            >>> cube.query(m["PnL x10"])
                                      PnL x10
            0  doubleVector[10]{-201.63, ...}

            >>> m["PnL /10"] = m["PnL.SUM"] / 10.0
            >>> cube.query(m["PnL /10"])
                                      PnL /10
            0  doubleVector[10]{-2.0163, ...}

    * Indexing:

        .. doctest:: array

            >>> m["First element"] = m["PnL.SUM"][0]
            >>> cube.query(m["First element"], m["PnL.SUM"])
              First element                         PnL.SUM
            0        -20.16  doubleVector[10]{-20.163, ...}

        This can be used with :meth:`atoti.cube.Cube.create_parameter_hierarchy_from_members` to "slice" the array:

        .. doctest:: array

            >>> cube.create_parameter_hierarchy_from_members(
            ...     "Index", list(range(0, 10))
            ... )
            >>> m["PnL at index"] = m["PnL.SUM"][l["Index"]]
            >>> cube.query(m["PnL at index"], levels=[l["Index"]])
                  PnL at index
            Index
            0           -20.16
            1           -14.97
            2          -110.10
            3           -76.30
            4              .48
            5           -57.51
            6             -.53
            7           -15.49
            8           -22.97
            9             9.26

        Non-integer hierarchies can also be created:

        .. doctest:: array

            >>> from datetime import date, timedelta
            >>> dates = [
            ...     date(2020, 1, 1) + timedelta(days=offset) for offset in range(0, 10)
            ... ]

            >>> cube.create_parameter_hierarchy_from_members(
            ...     "Dates", dates, index_measure_name="Date index"
            ... )
            >>> m["PnL at date"] = m["PnL.SUM"][m["Date index"]]
            >>> cube.query(m["Date index"], m["PnL at date"], levels=[l["Dates"]])
                       Date index PnL at date
            Dates
            2020-01-01          0      -20.16
            2020-01-02          1      -14.97
            2020-01-03          2     -110.10
            2020-01-04          3      -76.30
            2020-01-05          4         .48
            2020-01-06          5      -57.51
            2020-01-07          6        -.53
            2020-01-08          7      -15.49
            2020-01-09          8      -22.97
            2020-01-10          9        9.26

    * Slicing:

        .. doctest:: array

            >>> m["First 2 elements"] = m["PnL.SUM"][0:2]
            >>> cube.query(m["First 2 elements"], m["PnL.SUM"])
                            First 2 elements                         PnL.SUM
            0  doubleVector[2]{-20.163, ...}  doubleVector[10]{-20.163, ...}

"""

from __future__ import annotations

from typing import Mapping, Union, overload

from ._docs_utils import (
    QUANTILE_DOC,
    QUANTILE_INDEX_DOC,
    STD_AND_VAR_DOC,
    STD_DOC_KWARGS,
    VAR_DOC_KWARGS,
    doc,
)
from ._measures.calculated_measure import CalculatedMeasure, Operator
from ._measures.generic_measure import GenericMeasure
from ._operation import JavaFunctionOperation, Operation, _to_operation
from ._type_utils import (
    DataTypeError,
    PercentileIndexInterpolation,
    PercentileInterpolation,
    PercentileMode,
    VarianceMode,
    is_array,
)
from ._udaf_utils import array_mean, array_sum
from .column import Column
from .math import sqrt
from .measure import Measure
from .measure_description import MeasureDescription, _convert_to_measure_description

ArrayType = Union[Column, Operation]


def _check_array_type(measure: MeasureDescription):
    if isinstance(measure, Measure) and not is_array(measure.data_type):
        raise DataTypeError(measure, "array")


@overload
def sum(value: ArrayType) -> JavaFunctionOperation:  # pylint: disable=redefined-builtin
    ...


@overload
def sum(  # pylint: disable=redefined-builtin
    value: MeasureDescription,
) -> MeasureDescription:
    ...


def sum(  # pylint: disable=redefined-builtin
    value: Union[ArrayType, MeasureDescription],
) -> Union[JavaFunctionOperation, MeasureDescription]:
    """Return a measure equal to the sum of all the elements of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Sum"] = tt.array.sum(m["PnL.SUM"])
            >>> m["Empty sum"] = tt.array.sum(m["PnL.SUM"][0:0])
            >>> cube.query(m["Sum"], m["Empty sum"])
                   Sum Empty sum
            0  -308.29       .00

    """
    if isinstance(value, (Operation, Column)):
        return array_sum(_to_operation(value))

    measure = _convert_to_measure_description(value)
    _check_array_type(measure)
    return CalculatedMeasure(Operator("sum_vector", [measure]))


def positive_values(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure where all the elements < 0 of the passed array measure are replaced by 0."""
    _check_array_type(measure)
    return CalculatedMeasure(Operator("positive_vector", [measure]))


def negative_values(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure where all the elements > 0 of the passed array measure are replaced by 0."""
    _check_array_type(measure)
    return CalculatedMeasure(Operator("negative_vector", [measure]))


@overload
def mean(value: ArrayType) -> JavaFunctionOperation:
    ...


@overload
def mean(value: MeasureDescription) -> MeasureDescription:
    ...


def mean(
    value: Union[ArrayType, MeasureDescription]
) -> Union[MeasureDescription, JavaFunctionOperation]:
    """Return a measure equal to the mean of all the elements of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Mean"] = tt.array.mean(m["PnL.SUM"])
            >>> m["Empty mean"] = tt.array.mean(m["PnL.SUM"][0:0])
            >>> cube.query(m["Mean"], m["Empty mean"])
                 Mean Empty mean
            0  -30.83        .00

    """
    if isinstance(value, (Operation, Column)):
        return array_mean(_to_operation(value))
    _check_array_type(value)
    return CalculatedMeasure(Operator("mean_vector", [value]))


def prod(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the product of all the elements of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Product"] = tt.array.prod(m["PnL.SUM"])
            >>> m["Empty product"] = tt.array.prod(m["PnL.SUM"][0:0])
            >>> cube.query(m["Product"], m["Empty product"])
                          Product Empty product
            0  122,513,372,194.94          1.00

    """
    _check_array_type(measure)
    return CalculatedMeasure(Operator("product_vector", [measure]))


def min(  # pylint: disable=redefined-builtin
    measure: MeasureDescription,
) -> MeasureDescription:
    """Return a measure equal to the minimum element of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Min"] = tt.array.min(m["PnL.SUM"])
            >>> m["Empty min"] = tt.array.min(m["PnL.SUM"][0:0])
            >>> cube.query(m["Min"], m["Empty min"])
                   Min Empty min
            0  -110.10

    """
    _check_array_type(measure)
    return CalculatedMeasure(Operator("min_vector", [measure]))


def max(  # pylint: disable=redefined-builtin
    measure: MeasureDescription,
) -> MeasureDescription:
    """Return a measure equal to the maximum element of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Max"] = tt.array.max(m["PnL.SUM"])
            >>> m["Empty max"] = tt.array.max(m["PnL.SUM"][0:0])
            >>> cube.query(m["Max"], m["Empty max"])
                Max Empty max
            0  9.26


    """
    _check_array_type(measure)
    return CalculatedMeasure(Operator("max_vector", [measure]))


_QUANTILE_STD_AND_VAR_DOC_KWARGS = {
    "what": "of the elements of the passed array measure"
}


@doc(STD_AND_VAR_DOC, **{**VAR_DOC_KWARGS, **_QUANTILE_STD_AND_VAR_DOC_KWARGS})
def var(
    measure: MeasureDescription, *, mode: VarianceMode = "sample"
) -> MeasureDescription:
    _check_array_type(measure)
    return CalculatedMeasure(Operator("variance", [measure, mode]))


@doc(
    STD_AND_VAR_DOC,
    **{**STD_DOC_KWARGS, **_QUANTILE_STD_AND_VAR_DOC_KWARGS},
)
def std(
    measure: MeasureDescription, *, mode: VarianceMode = "sample"
) -> MeasureDescription:
    _check_array_type(measure)
    return sqrt(var(measure, mode=mode))


def sort(measure: MeasureDescription, *, ascending: bool = True) -> MeasureDescription:
    """Return an array measure with the elements of the passed array measure sorted.

    Example:
        .. doctest:: array

            >>> m["Sorted ascendingly"] = tt.array.sort(m["PnL.SUM"])
            >>> m["Sorted descendingly"] = tt.array.sort(m["PnL.SUM"], ascending=False)
            >>> cube.query(m["Sorted ascendingly"], m["Sorted descendingly"])
                                       Sorted ascendingly                       Sorted descendingly
            0  doubleVector[10]{-110.09900000000002, ...}  doubleVector[10]{9.259999999999998, ...}

    """
    _check_array_type(measure)
    return CalculatedMeasure(Operator("sort", [measure, str(ascending)]))


@doc(QUANTILE_DOC, **_QUANTILE_STD_AND_VAR_DOC_KWARGS)
def quantile(
    measure: MeasureDescription,
    q: Union[float, MeasureDescription],
    *,
    mode: PercentileMode = "inc",
    interpolation: PercentileInterpolation = "linear",
) -> MeasureDescription:
    if isinstance(q, float):
        if q < 0 or q > 1:
            raise ValueError("Quantile must be between 0 and 1.")
    _check_array_type(measure)
    return GenericMeasure(
        "CALCULATED_QUANTILE",
        mode,
        interpolation,
        [measure, _convert_to_measure_description(q)],
    )


@doc(QUANTILE_INDEX_DOC, **_QUANTILE_STD_AND_VAR_DOC_KWARGS)
def quantile_index(
    measure: MeasureDescription,
    q: Union[float, MeasureDescription],
    *,
    mode: PercentileMode = "inc",
    interpolation: PercentileIndexInterpolation = "lower",
) -> MeasureDescription:
    if isinstance(q, float):
        if q < 0 or q > 1:
            raise ValueError("Quantile must be between 0 and 1.")
    _check_array_type(measure)
    return GenericMeasure(
        "CALCULATED_QUANTILE_INDEX",
        mode,
        interpolation,
        [measure, _convert_to_measure_description(q)],
    )


def _validate_n_param(n: Union[int, MeasureDescription]):
    if isinstance(n, int):
        if n <= 0:
            raise ValueError("n must be greater than 0.")


def n_lowest(
    measure: MeasureDescription, n: Union[int, MeasureDescription]
) -> MeasureDescription:
    """Return an array measure containing the *n* lowest elements of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Bottom 3"] = tt.array.n_lowest(m["PnL.SUM"], n=3)
            >>> cube.query(m["Bottom 3"])
                                               Bottom 3
            0  doubleVector[3]{-57.51499999999999, ...}

    """
    _validate_n_param(n)
    _check_array_type(measure)
    return CalculatedMeasure(
        Operator("n_lowest", [measure, _convert_to_measure_description(n)])
    )


def n_lowest_indices(
    measure: MeasureDescription, n: Union[int, MeasureDescription]
) -> MeasureDescription:
    """Return an array measure containing the indices of the *n* lowest elements of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Bottom 3 indices"] = tt.array.n_lowest_indices(m["PnL.SUM"], n=3)
            >>> cube.query(m["Bottom 3 indices"])
                   Bottom 3 indices
            0  intVector[3]{2, ...}

    """
    _validate_n_param(n)
    _check_array_type(measure)
    return CalculatedMeasure(
        Operator("n_lowest_indices", [measure, _convert_to_measure_description(n)])
    )


def nth_lowest(
    measure: MeasureDescription, n: Union[int, MeasureDescription]
) -> MeasureDescription:
    """Return a measure equal to the *n*-th lowest element of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["3rd lowest"] = tt.array.nth_lowest(m["PnL.SUM"], n=3)
            >>> cube.query(m["3rd lowest"])
              3rd lowest
            0     -57.51

    """
    _validate_n_param(n)
    _check_array_type(measure)
    return CalculatedMeasure(
        Operator("nth_lowest", [measure, _convert_to_measure_description(n)])
    )


def n_greatest(
    measure: MeasureDescription, n: Union[int, MeasureDescription]
) -> MeasureDescription:
    """Return an array measure containing the *n* greatest elements of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Top 3"] = tt.array.n_greatest(m["PnL.SUM"], n=3)
            >>> cube.query(m["Top 3"])
                                                 Top 3
            0  doubleVector[3]{9.259999999999998, ...}

    """
    _validate_n_param(n)
    _check_array_type(measure)
    return CalculatedMeasure(
        Operator("n_greatest", [measure, _convert_to_measure_description(n)])
    )


def n_greatest_indices(
    measure: MeasureDescription, n: Union[int, MeasureDescription]
) -> MeasureDescription:
    """Return an array measure containing the indices of the *n* greatest elements of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Top 3 indices"] = tt.array.n_greatest_indices(m["PnL.SUM"], n=3)
            >>> cube.query(m["Top 3 indices"])
                      Top 3 indices
            0  intVector[3]{6, ...}

    """
    _validate_n_param(n)
    _check_array_type(measure)
    return CalculatedMeasure(
        Operator("n_greatest_indices", [measure, _convert_to_measure_description(n)])
    )


def nth_greatest(
    measure: MeasureDescription, n: Union[int, MeasureDescription]
) -> MeasureDescription:
    """Return a measure equal to the *n*-th greatest element of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["3rd greatest"] = tt.array.nth_greatest(m["PnL.SUM"], n=3)
            >>> cube.query(m["3rd greatest"])
              3rd greatest
            0         -.53

    """
    _validate_n_param(n)
    _check_array_type(measure)
    return CalculatedMeasure(
        Operator("nth_greatest", [measure, _convert_to_measure_description(n)])
    )


def len(  # pylint: disable=redefined-builtin
    measure: MeasureDescription,
) -> MeasureDescription:
    """Return a measure equal to the number of elements of the passed array measure.

    Example:
        .. doctest:: array

            >>> m["Length"] = tt.array.len(m["PnL.SUM"])
            >>> cube.query(m["Length"])
              Length
            0     10

    """
    _check_array_type(measure)
    return CalculatedMeasure(Operator("vector_length", [measure]))


def prefix_sum(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the sum of the previous elements in the passed array measure.

    Example:
        If an array has the following values: ``[2.0, 1.0, 0.0, 3.0]``, the returned array will be: ``[2.0, 3.0, 3.0, 6.0]``.
    """
    _check_array_type(measure)
    return CalculatedMeasure(Operator("prefix_sum", [measure]))


def replace(
    measure: MeasureDescription,
    replacements: Union[Mapping[float, float], Mapping[int, int]],
) -> MeasureDescription:
    """Return a measure where elements equal to a key of the *replacements* mapping are replaced with the corresponding value.

    Args:
        measure: The array measure in which to replace the elements.
        replacements: The mapping from the old values to the new ones.

    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Store ID", "New quantity", "Old quantity"],
        ...     data=[
        ...         (
        ...             "Store 1",
        ...             [12, 6, 2, 20],
        ...             [6, 3, 0, 10],
        ...         ),
        ...         ("Store 2", [16, 8, 12, 15], [4, 4, 6, 3]),
        ...         ("Store 3", [8, -10, 0, 33], [8, 0, 2, 11]),
        ...     ],
        ... )
        >>> table = session.read_pandas(df, table_name="Prices", keys=["Store ID"])
        >>> cube = session.create_cube(table)
        >>> l, m = cube.levels, cube.measures
        >>> m["Old quantity"] = tt.value(table["Old quantity"])
        >>> m["New quantity"] = tt.value(table["New quantity"])
        >>> m["Quantity ratio"] = m["New quantity"] / m["Old quantity"]
        >>> m["Quantity ratio"].formatter = "ARRAY[',']"
        >>> cube.query(m["Quantity ratio"], levels=[l["Store ID"]])
                         Quantity ratio
        Store ID
        Store 1    2.0,2.0,Infinity,2.0
        Store 2         4.0,2.0,2.0,5.0
        Store 3   1.0,-Infinity,0.0,3.0

        The function can be used to replace **infinity** with another value more suited to follow up computations:

        >>> import math
        >>> m["Quantity ratio without infinity"] = tt.array.replace(
        ...     m["Quantity ratio"], {math.inf: 1, -math.inf: -1}
        ... )
        >>> m["Quantity ratio without infinity"].formatter = "ARRAY[',']"
        >>> cube.query(m["Quantity ratio without infinity"], levels=[l["Store ID"]])
                 Quantity ratio without infinity
        Store ID
        Store 1                  2.0,2.0,1.0,2.0
        Store 2                  4.0,2.0,2.0,5.0
        Store 3                 1.0,-1.0,0.0,3.0
    """
    _check_array_type(measure)
    return GenericMeasure("VECTOR_REPLACE", replacements, [measure])
