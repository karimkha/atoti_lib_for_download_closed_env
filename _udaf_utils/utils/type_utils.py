from typing import Any, Iterable, Mapping

from ..._type_utils import is_array
from ...type import NULLABLE_DOUBLE_ARRAY, DataType

# Gives acceptable input types for ``JavaFunctions`` depending on the type requested in the function's signature
TYPE_CONSTRAINTS: Mapping[str, Iterable[str]] = {
    "double": ["double", "float", "long", "int"],
    "float": ["float", "long", "int"],
    "long": ["long", "int"],
    "int": ["int"],
    "double[]": ["double[]"],
    "float[]": ["float[]"],
    "long[]": ["long[]"],
    "int[]": ["int[]"],
    "object": ["object"],
}

# Currently supported types for Python constants.
PYTHON_TYPE_TO_JAVA_TYPE: Mapping[str, str] = {
    "str": "string",
    # Use the widest type to avoid compilation problems
    "int": "long",
    "float": "double",
}


def get_java_type(type_string: str) -> DataType:
    if type_string == "IVector":
        return NULLABLE_DOUBLE_ARRAY

    java_type = (
        type_string if type_string not in ["Boolean", "String"] else type_string.lower()
    )

    return DataType(java_type=java_type, nullable=True)  # type: ignore


def is_numeric_type(data_type: DataType) -> bool:
    """Checks if the data type is numeric."""
    return data_type.java_type in ["double", "float", "int", "long"]


def is_numeric_array_type(data_type: DataType) -> bool:
    """Checks if the data type is an array of numeric values."""
    return is_array(data_type) and not data_type.java_type == "Object[]"


def convert_python_type_to_java(value: Any):
    python_type = type(value).__name__
    java_type = PYTHON_TYPE_TO_JAVA_TYPE[python_type]
    if java_type is None:
        raise TypeError("Unsupported type: " + python_type)
    if python_type == "list":
        if not is_numeric_type(
            DataType(
                java_type=PYTHON_TYPE_TO_JAVA_TYPE[type(value[0]).__name__],  # type: ignore
                nullable=True,
            )
        ):
            raise TypeError("Only lists of numeric values are supported.")
        return DataType(
            java_type=PYTHON_TYPE_TO_JAVA_TYPE[type(value[0])] + "[]", nullable=True  # type: ignore
        )
    return DataType(java_type=java_type, nullable=True)  # type: ignore
