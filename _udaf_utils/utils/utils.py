"""Helper functions for converting operations into Java code."""
from typing import Optional

from ...column import Column
from ...type import BOOLEAN, DOUBLE, FLOAT, INT, LONG, DataType
from .type_utils import is_numeric_array_type

_BUFFER_WRITE_TEMPLATE = "{buffer_code}.{writer_code}(0, {value_code});"


def get_column_reader_code(column: Column, index: int):
    if column.data_type.java_type == BOOLEAN.java_type:
        return f"fact.readBoolean({index})"

    if column.data_type.java_type == INT.java_type:
        return f"fact.readInt({index})"

    if column.data_type.java_type == LONG.java_type:
        return f"fact.readLong({index})"

    if column.data_type.java_type == FLOAT.java_type:
        return f"fact.readFloat({index})"

    if column.data_type.java_type == DOUBLE.java_type:
        return f"fact.readDouble({index})"

    if is_numeric_array_type(column.data_type):
        return f"(fact.isNull({index}) ? null : fact.readVector({index}).cloneOnHeap())"

    raise TypeError("Unsupported column type: " + column.data_type.java_type)


def ensure_java_numeric_scalar_output_type(output_type: DataType):
    if output_type.java_type not in [
        DOUBLE.java_type,
        FLOAT.java_type,
        LONG.java_type,
        INT.java_type,
    ]:
        raise TypeError("Unsupported output type: " + output_type.java_type)


def get_buffer_read_code(*, buffer_code: str, output_type: DataType) -> str:
    ensure_java_numeric_scalar_output_type(output_type)

    method_name = f"read{output_type.java_type.capitalize()}"
    return f"{buffer_code}.{method_name}(0)"


def get_buffer_add_code(
    *, buffer_code: str, value_code: str, output_type: DataType
) -> str:
    ensure_java_numeric_scalar_output_type(output_type)
    writer_code = f"add{output_type.java_type.capitalize()}"
    return _BUFFER_WRITE_TEMPLATE.format(
        buffer_code=buffer_code, writer_code=writer_code, value_code=value_code
    )


def get_buffer_write_code(
    *, buffer_code: str, value_code: str, output_type: Optional[DataType]
) -> str:
    if output_type is None:
        return _BUFFER_WRITE_TEMPLATE.format(
            buffer_code=buffer_code, writer_code="write", value_code=value_code
        )

    ensure_java_numeric_scalar_output_type(output_type)

    writer_code = f"write{output_type.java_type.capitalize()}"
    return _BUFFER_WRITE_TEMPLATE.format(
        buffer_code=buffer_code, writer_code=writer_code, value_code=value_code
    )


def get_terminate_code(output_type: DataType, value_code: str) -> str:
    if output_type.java_type == DOUBLE.java_type:
        return f"Double.valueOf({value_code})"
    if output_type.java_type == FLOAT.java_type:
        return f"Float.valueOf({value_code})"
    if output_type.java_type == LONG.java_type:
        return f"Long.valueOf({value_code})"
    if output_type.java_type == INT.java_type:
        return f"Integer.valueOf({value_code})"

    raise TypeError("Unsupported output type: " + output_type.java_type)
