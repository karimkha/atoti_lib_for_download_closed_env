from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Tuple, Union

from typeguard import typeguard_ignore

from ._bitwise_operators_only import BitwiseOperatorsOnly
from ._operation import ColumnOperation, ConditionOperation, Operation
from .type import DataType

if TYPE_CHECKING:
    from .table import Table

# Type for table rows
Row = Union[Tuple[Any, ...], Dict[str, Any]]


@typeguard_ignore
@dataclass(frozen=True, eq=False)
class Column(BitwiseOperatorsOnly):
    """Column of a Table."""

    name: str
    """The name of the column."""

    data_type: DataType
    """The type of the elements in the column."""

    _table: Table = field(repr=False)

    def __mul__(self, other: Any) -> Operation:
        """Multiplication operator."""
        return ColumnOperation(self) * other

    def __rmul__(self, other: Any) -> Operation:
        """Multiplication operator."""
        return other * ColumnOperation(self)

    def __truediv__(self, other: Any) -> Operation:
        """Division operator."""
        return ColumnOperation(self) / other

    def __rtruediv__(self, other: Any) -> Operation:
        """Division operator."""
        return other / ColumnOperation(self)

    def __add__(self, other: Any) -> Operation:
        """Addition operator."""
        return ColumnOperation(self) + other

    def __radd__(self, other: Any) -> Operation:
        """Addition operator."""
        return other + ColumnOperation(self)

    def __sub__(self, other: Any) -> Operation:
        """Subtraction operator."""
        return ColumnOperation(self) - other

    def __rsub__(self, other: Any) -> Operation:
        """Subtraction operator."""
        return other - ColumnOperation(self)

    def __eq__(
        self, other: Any
    ) -> ConditionOperation:  # pyright: reportIncompatibleMethodOverride=false
        """Equal operator."""
        return ColumnOperation(self) == other

    def __ne__(
        self, other: Any
    ) -> ConditionOperation:  # pyright: reportIncompatibleMethodOverride=false
        """Not equal operator."""
        return ColumnOperation(self) != other

    def __lt__(self, other: Any) -> ConditionOperation:
        """Lower than operator."""
        return ColumnOperation(self) < other

    def __gt__(self, other: Any) -> ConditionOperation:
        """Greater than operator."""
        return ColumnOperation(self) > other

    def __le__(self, other: Any) -> ConditionOperation:
        """Lower than or equal operator."""
        return ColumnOperation(self) <= other

    def __ge__(self, other: Any) -> ConditionOperation:
        """Greater than or equal operator."""
        return ColumnOperation(self) >= other

    def _identity(self):
        return (self.name,) + self._table._identity()
