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


class SumAggregationOperationVisitor(AggregationOperationVisitor):
    """Implementation of the AggregationOperationVisitor to build the source code for a ``SUM`` aggregation function."""

    @staticmethod
    def _get_contribute_source_code(operation_element: JavaOperationElement) -> str:
        numeric_code = (
            get_buffer_add_code(
                buffer_code="aggregationBuffer",
                value_code="{java_source_code}",
                output_type=operation_element.output_type,
            )
            if is_numeric_type(operation_element.output_type)
            else None
        )
        array_code = dedent(
            """\
            if (aggregationBuffer.isNull(0)) {{
                aggregationBuffer.write(0, {java_source_code});
            }} else {{
                IVector value = {java_source_code};
                if (value != null) {{
                aggregationBuffer.readWritableVector(0).plus(value);
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
                value_code="{java_source_code}",
                output_type=operation_element.output_type,
            )
            if is_numeric_type(operation_element.output_type)
            else None
        )
        array_code = """\
            if (!aggregationBuffer.isNull(0)) {{
                aggregationBuffer.readWritableVector(0).minus({java_source_code});
            }}
        """
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
                        outputAggregationBuffer.readWritableVector(0).plus(inputAggregationBuffer.readVector(0));
                    }
                }
            """
            )
            return MERGE_TEMPLATE.format(body=body)

        raise TypeError("Unsupported output type " + str(operation_element.output_type))

    @staticmethod
    def _get_terminate_source_code(operation_element: JavaOperationElement) -> str:
        if is_numeric_type(operation_element.output_type):
            value = get_terminate_code(
                operation_element.output_type,
                get_buffer_read_code(
                    buffer_code="aggregationBuffer",
                    output_type=operation_element.output_type,
                ),
            )
            body = f"return {value};"
            return TERMINATE_TEMPLATE.format(body=body)
        if is_numeric_array_type(operation_element.output_type):
            body = dedent(
                """\
                return aggregationBuffer.readVector(0);
            """
            )
            return TERMINATE_TEMPLATE.format(body=body)
        raise TypeError("Unsupported output type " + str(operation_element.output_type))

    @staticmethod
    def _get_buffer_types(
        operation_element: JavaOperationElement,
    ) -> List[DataType]:
        return [operation_element.output_type]
