"""
Warning:
    Experimental features are subject to breaking changes (even removals) in minor and/or patch releases.

Financial functions.
"""

from ...hierarchy import Hierarchy
from ...measure_description import MeasureDescription
from ._irr import IrrMeasure


def irr(
    *,
    cash_flows: MeasureDescription,
    market_value: MeasureDescription,
    date: Hierarchy,
    precision: float = 0.001
) -> MeasureDescription:
    r"""Return the Internal Rate of Return based on the underlying cash flows and market values.

    The IRR is the rate ``r`` that nullifies the Net Present Value:

    .. math::

        NPV = \\sum_{i=0}^{T} CF_i (1 + r)^{\\frac{T - t_i}{T}} = 0

    With:

        * :math:`T` the total number of days since the beginning
        * :math:`t_i` the number of days since the beginning for date i
        * :math:`CF_i` the enhanced cashflow for date i:

            * CF of the first day is the opposite of the market value for this day: :math:`CF_0 = - MV_0`.
            * CF of the last day is increased by the market value for this day: :math:`CF_T = cash\\_flow_T + MV_T`.
            * Otherwise CF is the input cash flow: :math:`CF_i = cash\\_flow_i`.

    This equation is solved using the Newton's method.

    Args:
        cash_flows: The measure representing the cash flows.
        market_value: The measure representing the market value, used to enhanced the cashflows first and last value.
            If the cash flows don't need to be enhanced then ``0`` can be used.
        date: The date hierarchy. It must have a single date level.
        precision: The precision of the IRR value.

    See Also:
        The IRR `Wikipedia page <https://en.wikipedia.org/wiki/Internal_rate_of_return>`__.

    Example:

        With the following data:

        +------------+-------------+-------------------+
        | Date       | MarketValue | CashFlows         |
        +============+=============+===================+
        | 2020-01-01 | 1042749.90  |                   |
        +------------+-------------+-------------------+
        | 2020-01-02 | 1099720.01  |                   |
        +------------+-------------+-------------------+
        | 2020-01-03 | 1131220.24  |                   |
        +------------+-------------+-------------------+
        | 2020-01-04 | 1130904.32  |                   |
        +------------+-------------+-------------------+
        | 2020-01-05 | 1748358.77  | -582786.257893061 |
        +------------+-------------+-------------------+
        | 2020-01-06 | 1791552.54  |                   |
        +------------+-------------+-------------------+

        The IRR can be defined like this::

            m["irr"] = irr(cash_flows=m["CashFlow.SUM"], market_value=m["MarketValue.SUM"], date=h["Date"])
            cube.query(m["irr"])
            >>> 0.14397
    """
    if len(date.levels) > 1:
        raise ValueError("The date hierarchy must have a single date level")
    return IrrMeasure(cash_flows, market_value, date, precision)
