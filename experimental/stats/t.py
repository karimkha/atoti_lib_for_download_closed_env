"""Student’s t distribution.

For more information read:

    * `scipy.stats.t <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html>`__
    * `The Student’s t Wikipedia page <https://en.wikipedia.org/wiki/Student%27s_t-distribution>`__

"""

from ..._measures.calculated_measure import CalculatedMeasure, Operator
from ...measure_description import MeasureDescription, _convert_to_measure_description
from ._utils import NumericMeasureLike, ensure_strictly_positive


def pdf(
    point: MeasureDescription, *, degrees_of_freedom: NumericMeasureLike
) -> MeasureDescription:
    r"""Probability density function for a Student’s t distribution.

    The pdf of a Student's t-distribution is:

    .. math::

        \operatorname {pdf}(x)=\frac {\Gamma (\frac {\nu +1}{2})}{\sqrt {\nu \pi }\,\Gamma (\frac {\nu }{2})} \left(1+\frac {x^{2}}{\nu }\right)^{-\frac {\nu +1}{2}}

    where :math:`\nu` is the number of degrees of freedom and :math:`\Gamma` is the gamma function.

    Args:
        point: The point where the function is evaluated.
        degrees_of_freedom: The number of degrees of freedom.
            Must be positive.

    See Also:
        `The Student’s t Wikipedia page <https://en.wikipedia.org/wiki/Student%27s_t-distribution>`__

    """
    ensure_strictly_positive(degrees_of_freedom, "degrees_of_freedom")
    return CalculatedMeasure(
        Operator(
            "student_density",
            [point, _convert_to_measure_description(degrees_of_freedom)],
        )
    )


def cdf(
    point: MeasureDescription, *, degrees_of_freedom: NumericMeasureLike
) -> MeasureDescription:
    """Cumulative distribution function for a Student’s t distribution.

    Args:
        point: The point where the function is evaluated.
        degrees_of_freedom: The number of degrees of freedom.
            Must be positive.

    See Also:
        `The Student’s t Wikipedia page <https://en.wikipedia.org/wiki/Student%27s_t-distribution>`__

    """
    ensure_strictly_positive(degrees_of_freedom, "degrees_of_freedom")
    return CalculatedMeasure(
        Operator(
            "student_cumulative_probability",
            [point, _convert_to_measure_description(degrees_of_freedom)],
        )
    )


def ppf(
    point: MeasureDescription, *, degrees_of_freedom: NumericMeasureLike
) -> MeasureDescription:
    """Percent point function for a Student’s t distribution.

    Also called inverse cumulative distribution function.

    Args:
        point: The point where the function is evaluated.
        degrees_of_freedom: The number of degrees of freedom.
            Must be positive.

    See Also:
        `The Student’s t Wikipedia page <https://en.wikipedia.org/wiki/Student%27s_t-distribution>`__

    """
    ensure_strictly_positive(degrees_of_freedom, "degrees_of_freedom")
    return CalculatedMeasure(
        Operator(
            "student_ppf",
            [point, _convert_to_measure_description(degrees_of_freedom)],
        )
    )
