from __future__ import annotations

from typing import Optional, Union

from ...agg import ColumnOrOperation, MeasureOrMeasureConvertible, _agg
from ...measure_description import MeasureDescription
from ...scope.scope import Scope


def distinct(
    operand: Union[ColumnOrOperation, MeasureOrMeasureConvertible],
    *,
    scope: Optional[Scope] = None
) -> MeasureDescription:
    """Return an array measure representing the distinct values of the passed measure."""
    return _agg("DISTINCT", operand=operand, scope=scope)
