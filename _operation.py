from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Sequence

from ._bitwise_operators_only import BitwiseOperatorsOnly
from ._measures.literal_measure import LiteralMeasure
from ._measures.table_measure import TableMeasure
from .measure_description import MeasureDescription

if TYPE_CHECKING:
    from ._udaf_utils import JavaFunction, JavaOperationElement, OperationVisitor
    from .table import Column


def _to_operation(obj: Any) -> Operation:
    """Convert an object to an operation if is not already one.

    Args:
        obj: the object to convert.

    Returns:
        The operation corresponding to the given object.
    """
    if isinstance(obj, Operation):
        return obj

    if isinstance(obj, MeasureDescription):
        raise TypeError("MeasureDescriptions cannot be converted to an operation")

    from .table import Column  # pylint: disable=redefined-outer-name

    if isinstance(obj, Column):
        return ColumnOperation(obj)

    return ConstantOperation(obj)


def _get_new_columns(operation: Operation, column_names: Iterable[str]) -> List[Column]:
    columns: List[Column] = []
    for column in operation.columns:
        if not column.name in column_names:
            columns.append(column)
    return columns


class Operation(BitwiseOperatorsOnly):
    """An Operation between scalar and table columns."""

    @abstractmethod
    def accept(self, operation_visitor: OperationVisitor) -> JavaOperationElement:
        """Contribute this operation to the visitor."""

    @property
    @abstractmethod
    def columns(self) -> Sequence[Column]:
        """Columns involved in this operation."""

    def __mul__(self, other: Any) -> Operation:
        """Override the * operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return MultiplicationOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __rmul__(self, other: Any) -> Operation:
        """Override the * operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return MultiplicationOperation(other_op, self)
        except TypeError:
            return NotImplemented

    def __truediv__(self, other: Any) -> Operation:
        """Override the / operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return DivisionOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __rtruediv__(self, other: Any) -> Operation:
        """Override the / operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return DivisionOperation(other_op, self)
        except TypeError:
            return NotImplemented

    def __add__(self, other: Any) -> Operation:
        """Override the + operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return AdditionOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __radd__(self, other: Any) -> Operation:
        """Override the + operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return AdditionOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __sub__(self, other: Any) -> Operation:
        """Override the - operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return SubtractionOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __rsub__(self, other: Any) -> Operation:
        """Override the - operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return SubtractionOperation(other_op, self)
        except TypeError:
            return NotImplemented

    def __eq__(
        self, other: Any
    ) -> Operation:  # pyright: reportIncompatibleMethodOverride=false
        """Override the == operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return EqualOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __ne__(
        self, other: Any
    ) -> Operation:  # pyright: reportIncompatibleMethodOverride=false
        """Override the != operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return NotEqualOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __lt__(self, other: Any) -> Operation:
        """Override the < operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return LowerThanOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __gt__(self, other: Any) -> Operation:
        """Override the > operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return GreaterThanOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __le__(self, other: Any) -> Operation:
        """Override the <= operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return LowerThanOrEqualOperation(self, other_op)
        except TypeError:
            return NotImplemented

    def __ge__(self, other: Any) -> Operation:
        """Override the >= operator to delay the conversion."""
        try:
            other_op = _to_operation(other)
            return GreaterThanOrEqualOperation(self, other_op)
        except TypeError:
            return NotImplemented


class JavaFunctionOperation(Operation):
    @property
    @abstractmethod
    def underlyings(self) -> Sequence[Operation]:
        ...

    @property
    @abstractmethod
    def java_function(self) -> JavaFunction:
        ...

    def accept(self, operation_visitor: OperationVisitor) -> JavaOperationElement:
        return operation_visitor.visit_java_function_operation(self)

    @property
    def columns(self) -> Sequence[Column]:
        column_names = []
        columns = []
        for underlying in self.underlyings:
            new_columns = _get_new_columns(underlying, column_names)
            column_names += [column.name for column in new_columns]
            columns += new_columns
        return columns


@dataclass(frozen=True, eq=False)
class ColumnOperation(Operation):
    """Column of a table in an operation."""

    _column: Column

    def _to_measure_description(
        self, agg_fun: Optional[str] = None
    ) -> MeasureDescription:
        from ._functions import value

        return (
            TableMeasure(
                self._column,
                agg_fun,
                self._column._table,
            )
            if agg_fun
            else value(self._column)
        )

    def accept(self, operation_visitor: OperationVisitor) -> JavaOperationElement:
        return operation_visitor.visit_column_operation(self)

    @property
    def columns(self) -> Sequence[Column]:
        return [self._column]


@dataclass(frozen=True, eq=False)
class ConstantOperation(Operation):
    """Constant leaf of an operation."""

    _value: Any

    def accept(self, operation_visitor: OperationVisitor) -> JavaOperationElement:
        return operation_visitor.visit_constant_operation(self)

    @property
    def columns(self) -> Sequence[Column]:
        return []


@dataclass(eq=False, frozen=True)
class LeftRightOperation(JavaFunctionOperation):
    """Operation with left and right member."""

    _left: Operation
    _right: Operation

    @abstractmethod
    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        """Apply operation on measures."""

    @property
    def underlyings(self) -> Sequence[Operation]:
        return [self._left, self._right]


class MultiplicationOperation(LeftRightOperation):
    """Multiplication operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        """Apply operation on measures."""
        _throw_fact_level_operation(left, right)
        return left * right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import MUL_FUNCTION

        return MUL_FUNCTION


class AdditionOperation(LeftRightOperation):
    """Addition operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:  # pylint: disable=no-self-use
        _throw_fact_level_operation(left, right)
        return left + right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import ADD_FUNCTION

        return ADD_FUNCTION


class SubtractionOperation(LeftRightOperation):
    """Subtraction operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        _throw_fact_level_operation(left, right)
        return left - right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import SUB_FUNCTION

        return SUB_FUNCTION


class DivisionOperation(LeftRightOperation):
    """Division operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        _throw_fact_level_operation(left, right)
        return left / right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import TRUEDIV_FUNCTION

        return TRUEDIV_FUNCTION


@dataclass(frozen=True, eq=False)
class TernaryOperation(Operation):

    condition: ConditionOperation
    true_operation: Operation
    false_operation: Optional[Operation]

    def accept(self, operation_visitor: OperationVisitor) -> JavaOperationElement:
        return operation_visitor.visit_ternary_operation(self)

    @property
    def columns(self) -> Sequence[Column]:
        columns = []
        columns += self.condition.columns
        column_names = [column.name for column in columns]
        true_operation_columns = _get_new_columns(self.true_operation, column_names)
        columns += true_operation_columns
        column_names += [column.name for column in true_operation_columns]
        if self.false_operation is not None:
            columns += _get_new_columns(self.false_operation, column_names)
        return columns


class ConditionOperation(LeftRightOperation):
    """Operations which can be used as conditions."""


class EqualOperation(ConditionOperation):
    """== operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        _throw_fact_level_operation(left, right)
        return left == right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import EQ_FUNCTION

        return EQ_FUNCTION


class NotEqualOperation(ConditionOperation):
    """!= operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        _throw_fact_level_operation(left, right)
        return left != right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import NEQ_FUNCTION

        return NEQ_FUNCTION


class GreaterThanOperation(ConditionOperation):
    """> operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        _throw_fact_level_operation(left, right)
        return left > right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import GT_FUNCTION

        return GT_FUNCTION


class GreaterThanOrEqualOperation(ConditionOperation):
    """>= operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        _throw_fact_level_operation(left, right)
        return left >= right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import GTE_FUNCTION

        return GTE_FUNCTION


class LowerThanOperation(ConditionOperation):
    """< operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        _throw_fact_level_operation(left, right)
        return left < right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import LT_FUNCTION

        return LT_FUNCTION


class LowerThanOrEqualOperation(ConditionOperation):
    """<= operation."""

    def _apply_operation(
        self, left: MeasureDescription, right: MeasureDescription
    ) -> MeasureDescription:
        _throw_fact_level_operation(left, right)
        return left <= right

    @property
    def java_function(self) -> JavaFunction:
        from ._udaf_utils import LTE_FUNCTION

        return LTE_FUNCTION


def _throw_fact_level_operation(
    column1: MeasureDescription, column2: MeasureDescription
):
    """Raise an error because fact level operations are not supported in measures.

    Args:
        column1: the first column of the operation
        column2: the second column of the operation

    """
    if (isinstance(column1, TableMeasure) and isinstance(column2, LiteralMeasure)) or (
        isinstance(column1, LiteralMeasure) and isinstance(column2, TableMeasure)
    ):
        raise NotImplementedError(
            "It is not possible to create a measure by combining a table column"
            " and a constant. You can create a new table column instead."
        )
    if isinstance(column1, TableMeasure) and isinstance(column2, TableMeasure):
        raise NotImplementedError(
            "It is not possible to create a measure by combining 2 table columns."
            " You can create a new table column instead."
        )
