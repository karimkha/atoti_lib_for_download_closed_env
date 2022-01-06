from __future__ import annotations

from textwrap import dedent
from typing import List, Optional

from ...type import DataType
from ..java_operation_visitor import JavaOperationElement
from ..utils import (
    get_buffer_read_code,
    get_buffer_write_code,
    get_terminate_code,
    is_numeric_type,
)
from .aggregation_operation_visitor import (
    CONTRIBUTE_TEMPLATE,
    MERGE_TEMPLATE,
    TERMINATE_TEMPLATE,
    AggregationOperationVisitor,
)


def _get_numeric_code(operation_element: JavaOperationElement) -> str:
    output_type = operation_element.output_type
    buffer_value = get_buffer_read_code(
        buffer_code="aggregationBuffer", output_type=output_type
    )
    buffer_writer = get_buffer_write_code(
        buffer_code="aggregationBuffer", value_code="in", output_type=output_type
    )
    return dedent(
        """\
            {output_type} in = {{java_source_code}};
            if (aggregationBuffer.isNull(0)) {{{{
                {buffer_writer}
            }}}} else {{{{
                {output_type} buffer = {buffer_value};
                if (in < buffer) {{{{
                    {buffer_writer}
                }}}}
            }}}}
        """
    ).format(
        output_type=output_type.java_type,
        buffer_value=buffer_value,
        buffer_writer=buffer_writer,
    )


class MinAggregationOperationVisitor(AggregationOperationVisitor):
    """Implementation of the AggregationOperationVisitor to build the source code for a ``MIN`` aggregation function."""

    @staticmethod
    def _get_contribute_source_code(operation_element: JavaOperationElement) -> str:
        numeric_code = (
            _get_numeric_code(operation_element)
            if is_numeric_type(operation_element.output_type)
            else None
        )
        body = operation_element.get_java_source_code(numeric_code=numeric_code)
        return CONTRIBUTE_TEMPLATE.format(body=body)

    @staticmethod
    def _get_decontribute_source_code(
        operation_element: JavaOperationElement,  # pylint: disable=unused-argument
    ) -> Optional[str]:
        # Min cannot be de-aggregated
        return None

    @staticmethod
    def _get_merge_source_code(operation_element: JavaOperationElement) -> str:
        if is_numeric_type(operation_element.output_type):
            output_type = operation_element.output_type
            input_value = get_buffer_read_code(
                buffer_code="inputAggregationBuffer", output_type=output_type
            )
            output_value = get_buffer_read_code(
                buffer_code="outputAggregationBuffer", output_type=output_type
            )
            output_writer = get_buffer_write_code(
                buffer_code="outputAggregationBuffer",
                value_code="in",
                output_type=output_type,
            )
            body = dedent(
                """\
                    if (!inputAggregationBuffer.isNull(0)) {{{{
                        {output_type} in = {input_value};
                        if (outputAggregationBuffer.isNull(0)) {{{{
                            {output_writer}
                        }}}} else {{{{
                            {output_type} buffer = {output_value};
                            if (in < buffer) {{{{
                                {output_writer}
                            }}}}
                        }}}}
                    }}}}
                """
            ).format(
                output_type=output_type.java_type,
                input_value=input_value,
                output_value=output_value,
                output_writer=output_writer,
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
