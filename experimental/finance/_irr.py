from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ...hierarchy import Hierarchy
from ...measure_description import MeasureDescription

if TYPE_CHECKING:
    from ..._java_api import JavaApi
    from ...cube import Cube


@dataclass(eq=False)
class IrrMeasure(MeasureDescription):
    """Internal Rate of Return measure."""

    _cash_flows_measure: MeasureDescription
    _market_value_measure: MeasureDescription
    _date_hierarchy: Hierarchy
    _precision: float

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        # Distil the underlying measures
        cash_flows_name = self._cash_flows_measure._distil(
            java_api=java_api, cube=cube, measure_name=None
        )
        market_value_name = self._market_value_measure._distil(
            java_api=java_api, cube=cube, measure_name=None
        )

        distilled_name = java_api.create_measure(
            cube,
            measure_name,
            "IRR",
            market_value_name,  # market value first
            cash_flows_name,
            self._date_hierarchy._java_description,
            self._precision,
        )
        return distilled_name
