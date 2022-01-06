from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Collection, Iterable, Optional

from .._functions import value
from .._type_utils import is_array
from ..column import Column
from ..measure_description import MeasureDescription
from ..type import DOUBLE_ARRAY, NULLABLE_DOUBLE_ARRAY
from .calculated_measure import AggregatedMeasure
from .utils import get_measure_name

if TYPE_CHECKING:
    from .._java_api import JavaApi
    from ..cube import Cube


@dataclass(eq=False)
class SumProductFieldsMeasure(MeasureDescription):
    """Sum of the product of factors for table fields."""

    _factors: Collection[Column]

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        # Checks fields are in the selection, otherwise use the other sum product implementation because UDAF needs
        # fields in the selection.
        selection_fields = java_api.get_selection_fields(cube)
        if all(factor.name in selection_fields for factor in self._factors):
            factors_and_type = {}
            for factor in self._factors:
                if is_array(factor.data_type) and factor.data_type not in [
                    DOUBLE_ARRAY,
                    NULLABLE_DOUBLE_ARRAY,
                ]:
                    raise TypeError(
                        f"Unsupported operation. Only array columns of type double[] are supported and {factor} is not."
                    )
                factors_and_type[factor.name] = factor.data_type.java_type
            return java_api.create_measure(
                cube,
                measure_name,
                "SUM_PRODUCT_UDAF",
                [factor.name for factor in self._factors],
                factors_and_type,
            )
        return AggregatedMeasure(
            SumProductEncapsulationMeasure([value(factor) for factor in self._factors]),
            "SUM_PRODUCT",
            None,
        )._do_distil(java_api=java_api, cube=cube, measure_name=measure_name)


@dataclass(eq=False)
class SumProductEncapsulationMeasure(MeasureDescription):
    """Create an intermediate measure needing to be aggregated with the key "SUM_PRODUCT"."""

    _factors: Iterable[MeasureDescription]

    def _do_distil(
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:

        return java_api.create_measure(
            cube,
            measure_name,
            "SUM_PRODUCT_ENCAPSULATION",
            [
                get_measure_name(java_api=java_api, measure=factor, cube=cube)
                for factor in self._factors
            ],
        )
