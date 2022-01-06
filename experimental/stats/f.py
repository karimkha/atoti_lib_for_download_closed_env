"""F-distribution, also known as Snedecor's F distribution or the Fisher–Snedecor distribution.

For more information read:

    * `scipy.stats.f <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.f.html>`__
    * `The F-distribution Wikipedia page <https://en.wikipedia.org/wiki/F-distribution>`__

"""

from ..._measures.calculated_measure import CalculatedMeasure, Operator
from ...measure_description import MeasureDescription, _convert_to_measure_description
from ._utils import NumericMeasureLike, ensure_strictly_positive


def _validate_args(
    numerator_degrees_of_freedom: NumericMeasureLike,
    denominator_degrees_of_freedom: NumericMeasureLike,
):
    ensure_strictly_positive(
        numerator_degrees_of_freedom, "numerator_degrees_of_freedom"
    )
    ensure_strictly_positive(
        denominator_degrees_of_freedom, "denominator_degrees_of_freedom"
    )


def pdf(
    point: MeasureDescription,
    *,
    numerator_degrees_of_freedom: NumericMeasureLike,
    denominator_degrees_of_freedom: NumericMeasureLike
) -> MeasureDescription:
    r"""Probability density function for a F-distribution.

    The pdf for a F-distributions with parameters :math:`d1` et :math:`d2` is

    .. math::

        \operatorname {pdf}(x) = \frac
          {\sqrt {\frac {(d_{1}x)^{d_{1}}\,\,d_{2}^{d_{2}}}{(d_{1}x+d_{2})^{d_{1}+d_{2}}}}}
          {x\,\mathrm {B} \!\left(\frac {d_{1}}{2},\frac {d_{2}}{2}\right)}

    Where :math:`\mathrm {B}` is the beta function.

    Args:
        point: The point where the function is evaluated.
        numerator_degrees_of_freedom: Numerator degrees of freedom.
            Must be positive.
        denominator_degrees_of_freedom: Denominator degrees of freedom.
            Must be positive.

    See Also:
        `The F-distribution Wikipedia page <https://en.wikipedia.org/wiki/F-distribution>`__

    """
    _validate_args(numerator_degrees_of_freedom, denominator_degrees_of_freedom)
    return CalculatedMeasure(
        Operator(
            "F_density",
            [
                point,
                _convert_to_measure_description(numerator_degrees_of_freedom),
                _convert_to_measure_description(denominator_degrees_of_freedom),
            ],
        )
    )


def cdf(
    point: MeasureDescription,
    *,
    numerator_degrees_of_freedom: NumericMeasureLike,
    denominator_degrees_of_freedom: NumericMeasureLike
) -> MeasureDescription:
    r"""Cumulative distribution function for a F-distribution.

    The cdf for a F-distributions with parameters :math:`d1` et :math:`d2` is

     .. math::

        \operatorname {cdf}(x) = I_{\frac {d_{1}x}{d_{1}x+d_{2}}} \left(\tfrac {d_{1}}{2},\tfrac {d_{2}}{2}\right)

    where I is the `regularized incomplete beta function <https://en.wikipedia.org/wiki/Beta_function#Incomplete_beta_function>`__.

    Args:
        point: The point where the function is evaluated.
        numerator_degrees_of_freedom: Numerator degrees of freedom.
            Must be positive.
        denominator_degrees_of_freedom: Denominator degrees of freedom.
            Must be positive.

    See Also:
        `The F-distribution Wikipedia page <https://en.wikipedia.org/wiki/F-distribution>`__

    """
    _validate_args(numerator_degrees_of_freedom, denominator_degrees_of_freedom)
    return CalculatedMeasure(
        Operator(
            "F_cumulative_probability",
            [
                point,
                _convert_to_measure_description(numerator_degrees_of_freedom),
                _convert_to_measure_description(denominator_degrees_of_freedom),
            ],
        )
    )


def ppf(
    point: MeasureDescription,
    *,
    numerator_degrees_of_freedom: NumericMeasureLike,
    denominator_degrees_of_freedom: NumericMeasureLike
) -> MeasureDescription:
    """Percent point function for a F-distribution.

    Also called inverse cumulative distribution function.

    Args:
        point: The point where the function is evaluated.
        numerator_degrees_of_freedom: Numerator degrees of freedom.
            Must be positive.
        denominator_degrees_of_freedom: Denominator degrees of freedom.
            Must be positive.

    See Also:
        `The F-distribution Wikipedia page <https://en.wikipedia.org/wiki/F-distribution>`__

    """
    _validate_args(numerator_degrees_of_freedom, denominator_degrees_of_freedom)
    return CalculatedMeasure(
        Operator(
            "F_ppf",
            [
                point,
                _convert_to_measure_description(numerator_degrees_of_freedom),
                _convert_to_measure_description(denominator_degrees_of_freedom),
            ],
        )
    )
