from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Collection, Optional, Sequence

from .._operation import (
    ColumnOperation,
    ConstantOperation,
    JavaFunctionOperation,
    Operation,
    TernaryOperation,
)
from ..type import DataType
from .java_operation_element import JavaOperationElement

if TYPE_CHECKING:
    from .java_function import JavaFunction


class OperationVisitor(ABC):
    """Visitor class to create java operations."""

    @abstractmethod
    def build_java_operation(self, operation: Operation) -> JavaOperation:
        pass

    @abstractmethod
    def visit_column_operation(
        self, operation: ColumnOperation
    ) -> JavaOperationElement:
        """Convert a ``ColumnOperation`` into a ``JavaOperationElement``"""
        ...

    @abstractmethod
    def visit_constant_operation(
        self, operation: ConstantOperation
    ) -> JavaOperationElement:
        """Convert a ``ConstOperation`` into a ``JavaOperationElement``"""
        ...

    @abstractmethod
    def visit_ternary_operation(
        self, operation: TernaryOperation
    ) -> JavaOperationElement:
        """Convert a ``TernaryOperation`` into a ``JavaOperationElement``"""
        ...

    @abstractmethod
    def visit_java_function_operation(
        self, operation: JavaFunctionOperation
    ) -> JavaOperationElement:
        """Convert a ``JavaFunctionOperation`` into a ``JavaOperationElement``"""
        ...


@dataclass(frozen=True)
class JavaOperation:
    additional_imports: Collection[str]
    additional_methods_source_codes: Collection[str]
    contribute_source_code: str
    buffer_types: Sequence[DataType]
    decontribute_source_code: Optional[str]
    merge_source_code: str
    output_type: DataType
    terminate_source_code: str


@dataclass(frozen=True, eq=False)
class AppliedJavaFunctionOperation(JavaFunctionOperation):
    _underlyings: Sequence[Operation]
    _java_function: JavaFunction

    @property
    def java_function(self) -> JavaFunction:
        return self._java_function

    @property
    def underlyings(self) -> Sequence[Operation]:
        return self._underlyings
