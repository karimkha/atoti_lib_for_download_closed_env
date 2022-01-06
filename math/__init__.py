"""Measures can be combined with mathematical operators.

Several native Python operators are supported:

    - The classic ``+``, ``-`` and ``*`` operators

        .. doctest:: math

            >>> df = pd.DataFrame(
            ...     columns=["City", "A", "B", "C", "D"],
            ...     data=[
            ...         ("Berlin", 15.0, 10.0, 10.1, 1.0),
            ...         ("London", 24.0, 16.0, 20.5, 3.14),
            ...         ("New York", -27.0, 15.0, 30.7, 10.0),
            ...     ],
            ... )
            >>> table = session.read_pandas(df, keys=["City"], table_name="Math")
            >>> cube = session.create_cube(table)
            >>> l, m = cube.levels, cube.measures
            >>> m["Sum"] = m["A.SUM"] + m["B.SUM"]
            >>> m["Substract"] = m["A.SUM"] - m["B.SUM"]
            >>> m["Multiply"] = m["A.SUM"] * m["B.SUM"]
            >>> cube.query(
            ...     m["A.SUM"],
            ...     m["B.SUM"],
            ...     m["Sum"],
            ...     m["Substract"],
            ...     m["Multiply"],
            ...     levels=[l["City"]],
            ... )
                       A.SUM  B.SUM     Sum Substract Multiply
            City
            Berlin     15.00  10.00   25.00      5.00   150.00
            London     24.00  16.00   40.00      8.00   384.00
            New York  -27.00  15.00  -12.00    -42.00  -405.00

    - The float division ``/`` and integer division ``//``

        .. doctest:: math

            >>> m["Float division"] = m["A.SUM"] / m["B.SUM"]
            >>> m["Int division"] = m["A.SUM"] // m["B.SUM"]
            >>> cube.query(
            ...     m["A.SUM"],
            ...     m["B.SUM"],
            ...     m["Float division"],
            ...     m["Int division"],
            ...     levels=[l["City"]],
            ... )
                       A.SUM  B.SUM Float division Int division
            City
            Berlin     15.00  10.00           1.50         1.00
            London     24.00  16.00           1.50         1.00
            New York  -27.00  15.00          -1.80        -2.00

    - The exponentiation ``**``

        .. doctest:: math

            >>> m["a²"] = m["A.SUM"] ** 2
            >>> cube.query(m["A.SUM"], m["a²"], levels=[l["City"]])
                       A.SUM      a²
            City
            Berlin     15.00  225.00
            London     24.00  576.00
            New York  -27.00  729.00

    - The modulo ``%``

        .. doctest:: math

            >>> m["Modulo"] = m["A.SUM"] % m["B.SUM"]
            >>> cube.query(m["A.SUM"], m["B.SUM"], m["Modulo"], levels=[l["City"]])
                       A.SUM  B.SUM Modulo
            City
            Berlin     15.00  10.00   5.00
            London     24.00  16.00   8.00
            New York  -27.00  15.00   3.00

"""

from .._measures.calculated_measure import CalculatedMeasure, Operator
from ..measure_description import (
    MeasureDescription,
    MeasureLike,
    _convert_to_measure_description,
)


def abs(  # pylint: disable=redefined-builtin
    measure: MeasureDescription,
) -> MeasureDescription:
    """Return a measure equal to the absolute value of the passed measure.

    Example:
        .. doctest:: math

            >>> m["|A|"] = tt.math.abs(m["A.SUM"])
            >>> cube.query(m["A.SUM"], m["|A|"], levels=[l["City"]])
                       A.SUM    |A|
            City
            Berlin     15.00  15.00
            London     24.00  24.00
            New York  -27.00  27.00

    """
    return CalculatedMeasure(Operator("abs", [measure]))


def exp(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the exponential value of the passed measure.

    Example:
        .. doctest:: math

            >>> m["exp(D)"] = tt.math.exp(m["D.SUM"])
            >>> cube.query(m["D.SUM"], m["exp(D)"], levels=[l["City"]])
                      D.SUM     exp(D)
            City
            Berlin     1.00       2.72
            London     3.14      23.10
            New York  10.00  22,026.47

    """
    return CalculatedMeasure(Operator("exp", [measure]))


def log(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the natural logarithm (base *e*) of the passed measure.

    Example:
        .. doctest:: math

            >>> m["log(D)"] = tt.math.log(m["D.SUM"])
            >>> cube.query(m["D.SUM"], m["log(D)"], levels=[l["City"]])
                      D.SUM log(D)
            City
            Berlin     1.00    .00
            London     3.14   1.14
            New York  10.00   2.30

    """
    return CalculatedMeasure(Operator("log", [measure]))


def log10(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the base 10 logarithm of the passed measure.

    Example:
        .. doctest:: math

            >>> m["log10(D)"] = tt.math.log10(m["D.SUM"])
            >>> cube.query(m["D.SUM"], m["log10(D)"], levels=[l["City"]])
                      D.SUM log10(D)
            City
            Berlin     1.00      .00
            London     3.14      .50
            New York  10.00     1.00

    """
    return CalculatedMeasure(Operator("log10", [measure]))


def floor(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the largest integer <= to the passed measure.

    Example:
        .. doctest:: math

            >>> m["⌊C⌋"] = tt.math.floor(m["C.SUM"])
            >>> cube.query(m["C.SUM"], m["⌊C⌋"], levels=[l["City"]])
                      C.SUM ⌊C⌋
            City
            Berlin    10.10  10
            London    20.50  20
            New York  30.70  30

    """
    return CalculatedMeasure(Operator("floor", [measure]))


def ceil(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the smallest integer that is >= to the passed measure.

    Example:
        .. doctest:: math

            >>> m["⌈C⌉"] = tt.math.ceil(m["C.SUM"])
            >>> cube.query(m["C.SUM"], m["⌈C⌉"], levels=[l["City"]])
                      C.SUM ⌈C⌉
            City
            Berlin    10.10  11
            London    20.50  21
            New York  30.70  31

    """
    return CalculatedMeasure(Operator("ceil", [measure]))


def round(  # pylint: disable=redefined-builtin
    measure: MeasureDescription,
) -> MeasureDescription:
    """Return a measure equal to the closest integer to the passed measure.

    Note:
        To change how a measure is displayed, use a :attr:`~atoti.measure.Measure.formatter` instead.

    Example:
        .. doctest:: math

            >>> m["round(C)"] = tt.math.round(m["C.SUM"])
            >>> cube.query(m["C.SUM"], m["round(C)"], levels=[l["City"]])
                      C.SUM round(C)
            City
            Berlin    10.10       10
            London    20.50       21
            New York  30.70       31

    """
    return CalculatedMeasure(Operator("round", [measure]))


def sin(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the sine of the passed measure in radians.

    Example:
        .. doctest:: math

            >>> m["sin(D)"] = tt.math.sin(m["D.SUM"])
            >>> cube.query(m["D.SUM"], m["sin(D)"], levels=[l["City"]])
                      D.SUM sin(D)
            City
            Berlin     1.00    .84
            London     3.14    .00
            New York  10.00   -.54

    """
    return CalculatedMeasure(Operator("sin", [measure]))


def cos(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the cosine of the passed measure in radians.

    Example:
        .. doctest:: math

            >>> m["cos(D)"] = tt.math.cos(m["D.SUM"])
            >>> cube.query(m["D.SUM"], m["cos(D)"], levels=[l["City"]])
                      D.SUM cos(D)
            City
            Berlin     1.00    .54
            London     3.14  -1.00
            New York  10.00   -.84

    """
    return CalculatedMeasure(Operator("cos", [measure]))


def tan(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the tangent of the passed measure in radians.

    Example:
        .. doctest:: math

            >>> m["tan(D)"] = tt.math.tan(m["D.SUM"])
            >>> cube.query(m["D.SUM"], m["tan(D)"], levels=[l["City"]])
                      D.SUM tan(D)
            City
            Berlin     1.00   1.56
            London     3.14   -.00
            New York  10.00    .65
    MeasureDescription
    """
    return CalculatedMeasure(Operator("tan", [measure]))


def sqrt(measure: MeasureDescription) -> MeasureDescription:
    """Return a measure equal to the square root of the passed measure.

    Example:
        .. doctest:: math

            >>> m["√B"] = tt.math.sqrt(m["B.SUM"])
            >>> cube.query(m["B.SUM"], m["√B"], levels=[l["City"]])
                      B.SUM    √B
            City
            Berlin    10.00  3.16
            London    16.00  4.00
            New York  15.00  3.87
    MeasureDescription
    """
    return measure ** 0.5


def max(  # pylint: disable=redefined-builtin
    *measures: MeasureLike,
) -> MeasureDescription:
    """Return a measure equal to the maximum of the passed arguments.

    Example:
        .. doctest:: math

            >>> m["max"] = tt.math.max(m["A.SUM"], m["B.SUM"])
            >>> cube.query(m["A.SUM"], m["B.SUM"], m["max"], levels=[l["City"]])
                       A.SUM  B.SUM    max
            City
            Berlin     15.00  10.00  15.00
            London     24.00  16.00  24.00
            New York  -27.00  15.00  15.00

    """
    if len(measures) < 2:
        raise ValueError(
            "This function is not made to compute the maximum of a single measure."
            " To find the maximum value of this measure on the levels it is expressed,"
            " use atoti.agg.max() instead."
        )
    return CalculatedMeasure(
        Operator(
            "max", [_convert_to_measure_description(measure) for measure in measures]
        )
    )


def min(  # pylint: disable=redefined-builtin
    *measures: MeasureLike,
) -> MeasureDescription:
    """Return a measure equal to the minimum of the passed arguments.

    Example:
        .. doctest:: math

            >>> m["min"] = tt.math.min(m["A.SUM"], m["B.SUM"])
            >>> cube.query(m["A.SUM"], m["B.SUM"], m["min"], levels=[l["City"]])
                       A.SUM  B.SUM     min
            City
            Berlin     15.00  10.00   10.00
            London     24.00  16.00   16.00
            New York  -27.00  15.00  -27.00

    """
    if len(measures) < 2:
        raise ValueError(
            "You can not calculate the min of a single measure using this function. "
            "If you want to find the minimum value of this measure on the levels it is defined on, use atoti.agg.min"
        )
    return CalculatedMeasure(
        Operator(
            "min", [_convert_to_measure_description(measure) for measure in measures]
        )
    )


def erf(measure: MeasureLike) -> MeasureDescription:
    """Return the error function of the input measure.

    This can be used to compute traditional statistical measures such as the cumulative standard normal distribution.

    For more information read:

      * Python's built-in :func:`math.erf`
      * `scipy.special.erf <https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.erf.html>`__
      * `The Wikipedia page <https://en.wikipedia.org/wiki/Error_function#Numerical_approximations>`__

    Example:
        .. doctest:: math

            >>> m["erf"] = tt.math.erf(m["D.SUM"])
            >>> m["erf"].formatter = "DOUBLE[#,##0.000000]"
            >>> cube.query(m["D.SUM"], m["erf"], levels=[l["City"]])
                      D.SUM       erf
            City
            Berlin     1.00  0.842701
            London     3.14  0.999991
            New York  10.00  1.000000

    """
    return CalculatedMeasure(
        Operator("erf", [_convert_to_measure_description(measure)])
    )


def erfc(measure: MeasureLike) -> MeasureDescription:
    """Return the complementary error function of the input measure.

    This is the complementary of :func:`atoti.math.erf`.
    It is defined as ``1.0 - erf``.
    It can be used for large values of x where a subtraction from one would cause a loss of significance.

    Example:
        .. doctest:: math

            >>> m["erfc"] = tt.math.erfc(m["D.SUM"])
            >>> m["1-erf"] = 1 - tt.math.erf(m["D.SUM"])
            >>> m["erfc"].formatter = "DOUBLE[#.00E]"
            >>> m["1-erf"].formatter = "DOUBLE[#.00E]"
            >>> cube.query(m["D.SUM"], m["erfc"], m["1-erf"], levels=[l["City"]])
                      D.SUM                    erfc                1-erf
            City
            Berlin     1.00     0.15729920705028488  0.15729920705028488
            London     3.14    8.969565553264981E-6   8.9695655532962E-6
            New York  10.00  2.0884875837625685E-45                  0.0

    """
    return CalculatedMeasure(
        Operator("erfc", [_convert_to_measure_description(measure)])
    )
