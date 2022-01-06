from __future__ import annotations

from abc import ABC, abstractmethod
from textwrap import dedent
from typing import List, Optional, Sequence, Set

from atoti._udaf_utils.utils.type_utils import convert_python_type_to_java

from ..._java_api import JavaApi
from ..._operation import (
    ColumnOperation,
    ConstantOperation,
    JavaFunctionOperation,
    Operation,
    TernaryOperation,
)
from ...type import DataType
from ..java_operation_element import (
    BasicJavaOperationElement,
    JavaOperationElement,
    TernaryJavaOperationElement,
)
from ..java_operation_visitor import JavaOperation, OperationVisitor
from ..utils import get_column_reader_code

CONTRIBUTE_TEMPLATE = dedent(
    """\
protected void contribute(IArrayReader fact, IWritableBuffer aggregationBuffer) {{
    {body}
}}
"""
)

DECONTRIBUTE_TEMPLATE = dedent(
    """\
protected void decontribute(IArrayReader fact, IWritableBuffer aggregationBuffer) {{
    {body}
}}
"""
)

MERGE_TEMPLATE = dedent(
    """\
protected void merge(IArrayReader inputAggregationBuffer, IWritableBuffer outputAggregationBuffer) {{
    {body}
}}
"""
)

TERMINATE_TEMPLATE = dedent(
    """\
protected Object terminate(IArrayReader aggregationBuffer) {{
    {body}
}}
"""
)


class AggregationOperationVisitor(OperationVisitor, ABC):
    """Base OperationVisitor for building Java code for an aggregation function."""

    def __init__(self, *, column_names: Sequence[str], java_api: JavaApi):
        self.column_names = column_names
        self.additional_methods_source_codes: Set[str] = set()
        self.additional_imports: Set[str] = set()
        self.java_api = java_api

    def build_java_operation(self, operation: Operation) -> JavaOperation:
        operation_element = operation.accept(self)
        return JavaOperation(
            additional_imports=self.additional_imports,
            additional_methods_source_codes=self.additional_methods_source_codes,
            contribute_source_code=self._get_contribute_source_code(operation_element),
            decontribute_source_code=self._get_decontribute_source_code(
                operation_element
            ),
            merge_source_code=self._get_merge_source_code(operation_element),
            terminate_source_code=self._get_terminate_source_code(operation_element),
            buffer_types=self._get_buffer_types(operation_element),
            output_type=operation_element.output_type,
        )

    @staticmethod
    @abstractmethod
    def _get_contribute_source_code(operation_element: JavaOperationElement) -> str:
        ...

    @staticmethod
    @abstractmethod
    def _get_decontribute_source_code(
        operation_element: JavaOperationElement,
    ) -> Optional[str]:
        ...

    @staticmethod
    @abstractmethod
    def _get_merge_source_code(operation_element: JavaOperationElement) -> str:
        ...

    @staticmethod
    @abstractmethod
    def _get_terminate_source_code(operation_element: JavaOperationElement) -> str:
        ...

    @staticmethod
    @abstractmethod
    def _get_buffer_types(
        operation_element: JavaOperationElement,
    ) -> List[DataType]:
        ...

    def visit_column_operation(
        self, operation: ColumnOperation
    ) -> JavaOperationElement:
        name = operation._column.name
        column = operation._column
        return BasicJavaOperationElement(
            java_source_code=get_column_reader_code(
                column, self.column_names.index(name)
            ),
            _output_type=column.data_type,
        )

    def visit_constant_operation(  # pylint: disable=no-self-use
        self, operation: ConstantOperation
    ) -> JavaOperationElement:
        return BasicJavaOperationElement(
            java_source_code=f"{operation._value}",
            _output_type=convert_python_type_to_java(operation._value),
        )

    def visit_ternary_operation(
        self, operation: TernaryOperation
    ) -> JavaOperationElement:
        condition = operation.condition.accept(self)
        true_value = operation.true_operation.accept(self)
        false_value = (
            operation.false_operation.accept(self)
            if operation.false_operation is not None
            else None
        )
        if not isinstance(condition, BasicJavaOperationElement):
            raise TypeError(
                "Only BasicJavaOperationElements can be used as conditions, got "
                + str(condition)
            )
        return TernaryJavaOperationElement(
            condition_java_operation=condition,
            true_statement_java_operation=true_value,
            false_statement_java_operation=false_value,
        )

    def visit_java_function_operation(
        self, operation: JavaFunctionOperation
    ) -> JavaOperationElement:
        java_function = operation.java_function
        # If the operation is a ternary operation, we need to bubble up the condition so they are all applied before any calculations are performed
        # i.e. (a < 2 ? (b > 3 ? c * 2, 3) + 2 : 3) would give us:
        # if (a < 2):
        #   if (b > 3):
        #       c * 2 + 2
        #   else:
        #       3 + 2
        # else:
        #   3
        # This makes it much easier to type check the various stages of the calculation and avoid errors when compiling the java code
        for index, underlying in enumerate(operation.underlyings):
            if isinstance(underlying, TernaryOperation):
                # Replace the TernaryOperation with the true operation
                true_operations = list(operation.underlyings)
                true_operations[index] = underlying.true_operation
                false_operations = list(operation.underlyings)
                if underlying.false_operation is not None:
                    # replace the ternary operation with the false operation
                    false_operations[index] = underlying.false_operation
                return TernaryOperation(
                    condition=underlying.condition,
                    # Call the java function on the new true_operations
                    true_operation=java_function(true_operations),
                    # Call the java function on the new false operations
                    false_operation=java_function(false_operations)
                    if underlying.false_operation is not None
                    else None,
                ).accept(self)
        # Once there are no more TernaryOperations in the underlyings, we can procede
        java_function.add_method_source_codes(self.additional_methods_source_codes)
        java_function.update_class_imports(self.additional_imports)
        operation_elements = [
            underlying.accept(self) for underlying in operation.underlyings
        ]
        java_source_code = java_function.get_java_source_code(
            *operation_elements, java_api=self.java_api
        )
        return BasicJavaOperationElement(
            java_source_code=java_source_code,
            _output_type=java_function.get_output_type_function()(
                operation_elements, self.java_api
            ),
        )
