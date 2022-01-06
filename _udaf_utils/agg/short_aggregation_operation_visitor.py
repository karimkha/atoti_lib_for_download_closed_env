from __future__ import annotations

from textwrap import dedent
from typing import List, Optional

from ...type import DataType
from ..java_operation_visitor import JavaOperationElement
from ..utils import (
    get_buffer_add_code,
    get_buffer_read_code,
    get_terminate_code,
    is_numeric_array_type,
    is_numeric_type,
)
from .aggregation_operation_visitor import (
    CONTRIBUTE_TEMPLATE,
    DECONTRIBUTE_TEMPLATE,
    MERGE_TEMPLATE,
    TERMINATE_TEMPLATE,
    AggregationOperationVisitor,
)


class ShortAggregationOperationVisitor(AggregationOperationVisitor):
    """Implementation of the AggregationOperationVisitor to build the source code for a ``SHORT`` aggregation function."""

    @staticmethod
    def _get_contribute_source_code(operation_element: JavaOperationElement) -> str:
        numeric_code = (
            get_buffer_add_code(
                buffer_code="aggregationBuffer",
                value_code="Math.min(0.0, {java_source_code})",
                output_type=operation_element.output_type,
            )
            if is_numeric_type(operation_element.output_type)
            else None
        )
        array_code = dedent(
            """\
            IVector value = {java_source_code};
            if (value != null) {{
                if (aggregationBuffer.isNull(0)) {{
                    aggregationBuffer.write(0, new NegativeVector(value));
                }} else {{
                    aggregationBuffer.readWritableVector(0).plusNegativeValues(value);
                }}
            }}
        """
        )
        body = operation_element.get_java_source_code(
            numeric_code=numeric_code,
            array_code=array_code,
        )
        return CONTRIBUTE_TEMPLATE.format(body=body)

    @staticmethod
    def _get_decontribute_source_code(
        operation_element: JavaOperationElement,
    ) -> Optional[str]:
        numeric_code = (
            get_buffer_add_code(
                buffer_code="aggregationBuffer",
                value_code="-1 * Math.min(0.0, {java_source_code})",
                output_type=operation_element.output_type,
            )
            if is_numeric_type(operation_element.output_type)
            else None
        )
        array_code = "aggregationBuffer.readWritableVector(0).minusNegativeValues({java_source_code});"
        body = operation_element.get_java_source_code(
            numeric_code=numeric_code,
            array_code=array_code,
        )
        return DECONTRIBUTE_TEMPLATE.format(body=body)

    @staticmethod
    def _get_merge_source_code(operation_element: JavaOperationElement) -> str:
        if is_numeric_type(operation_element.output_type):
            body = get_buffer_add_code(
                buffer_code="outputAggregationBuffer",
                value_code=get_buffer_read_code(
                    buffer_code="inputAggregationBuffer",
                    output_type=operation_element.output_type,
                ),
                output_type=operation_element.output_type,
            )
            return MERGE_TEMPLATE.format(body=body)

        if is_numeric_array_type(operation_element.output_type):
            body = dedent(
                """\
            if (!inputAggregationBuffer.isNull(0)) {
                if (outputAggregationBuffer.isNull(0)) {
                    outputAggregationBuffer.write(0, inputAggregationBuffer.readVector(0));
                } else {
                    outputAggregationBuffer.readWritableVector(0).plusNegativeValues(inputAggregationBuffer.readVector(0));
                }
            }
            """
            )
            return MERGE_TEMPLATE.format(body=body)

        raise TypeError("Unsupported output type " + str(operation_element.output_type))

    @staticmethod
    def _get_terminate_source_code(operation_element: JavaOperationElement) -> str:
        if is_numeric_type(operation_element.output_type):
            return_value = get_terminate_code(
                operation_element.output_type,
                get_buffer_read_code(
                    buffer_code="aggregationBuffer",
                    output_type=operation_element.output_type,
                ),
            )
            body = f"return {return_value};"
            return TERMINATE_TEMPLATE.format(body=body)

        if is_numeric_array_type(operation_element.output_type):
            body = "return aggregationBuffer.readVector(0);"
            return TERMINATE_TEMPLATE.format(body=body)

        raise TypeError("Unsupported output type " + str(operation_element.output_type))

    @staticmethod
    def _get_buffer_types(
        operation_element: JavaOperationElement,
    ) -> List[DataType]:
        return [operation_element.output_type]
