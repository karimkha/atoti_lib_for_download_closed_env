from __future__ import annotations

from textwrap import dedent
from typing import List, Optional

from atoti._udaf_utils.utils.utils import get_terminate_code

from ...type import DataType
from ..java_operation_visitor import JavaOperationElement
from ..utils import get_buffer_read_code, get_buffer_write_code, is_numeric_type
from .aggregation_operation_visitor import (
    CONTRIBUTE_TEMPLATE,
    DECONTRIBUTE_TEMPLATE,
    MERGE_TEMPLATE,
    TERMINATE_TEMPLATE,
    AggregationOperationVisitor,
)


def _get_contribute_numeric_code(
    operation_element: JavaOperationElement,
) -> str:
    output_type = operation_element.output_type
    multiplication_code = (
        get_buffer_read_code(buffer_code="aggregationBuffer", output_type=output_type)
        + "* {java_source_code}"
    )
    write_input = get_buffer_write_code(
        buffer_code="aggregationBuffer",
        value_code="{java_source_code}",
        output_type=output_type,
    )
    write_multiplication = get_buffer_write_code(
        buffer_code="aggregationBuffer",
        value_code=multiplication_code,
        output_type=output_type,
    )
    return dedent(
        """\
            if (aggregationBuffer.isNull(0)) {{{{
                {write_input}
            }}}} else {{{{
                {write_multiplication}
            }}}}
        """
    ).format(write_input=write_input, write_multiplication=write_multiplication)


def _get_decontribute_numeric_code(
    operation_element: JavaOperationElement,
) -> str:
    division_code = (
        get_buffer_read_code(
            buffer_code="aggregationBuffer",
            output_type=operation_element.output_type,
        )
        + "/ {java_source_code}"
    )
    return get_buffer_write_code(
        buffer_code="aggregationBuffer",
        value_code=division_code,
        output_type=operation_element.output_type,
    )


class MultiplyAggregationOperationVisitor(AggregationOperationVisitor):
    """Implementation of the AggregationOperationVisitor to build the source code for a ``MULTIPLIY`` aggregation function."""

    @staticmethod
    def _get_contribute_source_code(operation_element: JavaOperationElement) -> str:
        numeric_code = (
            _get_contribute_numeric_code(operation_element)
            if (is_numeric_type(operation_element.output_type))
            else None
        )
        body = operation_element.get_java_source_code(numeric_code=numeric_code)
        return CONTRIBUTE_TEMPLATE.format(body=body)

    @staticmethod
    def _get_decontribute_source_code(
        operation_element: JavaOperationElement,
    ) -> Optional[str]:
        numeric_code = (
            _get_decontribute_numeric_code(operation_element)
            if is_numeric_type(operation_element.output_type)
            else None
        )
        body = operation_element.get_java_source_code(numeric_code=numeric_code)
        return DECONTRIBUTE_TEMPLATE.format(body=body)

    @staticmethod
    def _get_merge_source_code(operation_element: JavaOperationElement) -> str:
        if is_numeric_type(operation_element.output_type):
            output_value = get_buffer_read_code(
                buffer_code="outputAggregationBuffer",
                output_type=operation_element.output_type,
            )
            input_value = get_buffer_read_code(
                buffer_code="inputAggregationBuffer",
                output_type=operation_element.output_type,
            )
            body = get_buffer_write_code(
                buffer_code="outputAggregationBuffer",
                value_code=f"{output_value} * {input_value}",
                output_type=operation_element.output_type,
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

        raise TypeError("Unsupported output type " + str(operation_element.output_type))

    @staticmethod
    def _get_buffer_types(
        operation_element: JavaOperationElement,
    ) -> List[DataType]:
        return [operation_element.output_type]
