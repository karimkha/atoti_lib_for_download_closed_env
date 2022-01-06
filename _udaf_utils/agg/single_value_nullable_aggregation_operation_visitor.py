from __future__ import annotations

from textwrap import dedent
from typing import List, Optional

from atoti._udaf_utils.java_operation_element import is_numeric_array_type

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


def _get_contribute_numeric_code(
    operation_element: JavaOperationElement,
) -> str:
    output_type = operation_element.output_type
    write_input = get_buffer_write_code(
        buffer_code="aggregationBuffer", value_code="in", output_type=output_type
    )
    write_null = get_buffer_write_code(
        buffer_code="aggregationBuffer", value_code="null", output_type=None
    )
    buffer_value = get_buffer_read_code(
        buffer_code="aggregationBuffer", output_type=output_type
    )
    return dedent(
        """\
        {output_type} in = {{java_source_code}};
        if (aggregationBuffer.isNull(0)) {{{{
            {write_input}
        }}}} else {{{{
            {output_type} buffer = {buffer_value};
            if (buffer != in) {{{{
                {write_null}
            }}}}
        }}}}
    """
    ).format(
        output_type=output_type.java_type,
        write_input=write_input,
        buffer_value=buffer_value,
        write_null=write_null,
    )


class SingleValueNullableAggregationOperationVisitor(AggregationOperationVisitor):
    """Implementation of the AggregationOperationVisitor to build the source code for a ``SINGLE_VALUE_NULLABLE`` aggregation function."""

    @staticmethod
    def _get_contribute_source_code(
        operation_element: JavaOperationElement,
    ) -> str:
        numeric_code = (
            _get_contribute_numeric_code(operation_element)
            if is_numeric_type(operation_element.output_type)
            else None
        )
        array_code = dedent(
            """\
        if (aggregationBuffer.isNull(0)) {{
            aggregationBuffer.write(0, {java_source_code});
        }} else {{
            IVector in = {java_source_code};
            IVector out = aggregationBuffer.readVector(0);
            if (!out.equals(in)) {{
                aggregationBuffer.write(0, null);
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
        operation_element: JavaOperationElement,  # pylint: disable=unused-argument
    ) -> Optional[str]:
        # Single value cannot be de-aggregated
        return None

    @staticmethod
    def _get_merge_source_code(
        operation_element: JavaOperationElement,
    ) -> str:
        if is_numeric_type(operation_element.output_type):
            output_type = operation_element.output_type
            read_input = get_buffer_read_code(
                buffer_code="inputAggregationBuffer", output_type=output_type
            )
            read_output = get_buffer_read_code(
                buffer_code="outputAggregationBuffer", output_type=output_type
            )
            write_null = get_buffer_write_code(
                buffer_code="outputAggregationBuffer",
                value_code="null",
                output_type=None,
            )
            body = f"if ({read_input} != {read_output}) {{\n" f"  {write_null}\n" f"}}"
            return MERGE_TEMPLATE.format(body=body)
        if is_numeric_array_type(operation_element.output_type):
            body = dedent(
                """\
            if (!inputAggregationBuffer.readVector(0).equals(outputAggregationBuffer.readVector(0))) {
                outputAggregationBuffer.write(0, null);
            }
            """
            )
            return MERGE_TEMPLATE.format(body=body)
        raise TypeError("Unsupported output type " + str(operation_element.output_type))

    @staticmethod
    def _get_terminate_source_code(
        operation_element: JavaOperationElement,
    ) -> str:
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
