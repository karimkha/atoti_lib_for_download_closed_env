from dataclasses import dataclass

from typing_extensions import Literal

JavaType = Literal[
    "boolean",
    "string",
    "int",
    "int[]",
    "long",
    "long[]",
    "float",
    "float[]",
    "double",
    "double[]",
    "Object",
    "Object[]",
    "LocalDate",
    "LocalDateTime",
    "LocalTime",
    "ZonedDateTime",
]


@dataclass(frozen=True)
class DataType:
    """atoti Type."""

    java_type: JavaType
    """Name of the associated Java type."""

    nullable: bool
    """Whether the objects of this type can be ``None``.

    Elements within array types cannot be ``None`` and must share the same scalar type.
    """

    def __init__(self, *, java_type: JavaType, nullable: bool):
        self.__dict__["java_type"] = java_type
        self.__dict__["nullable"] = nullable

    def __str__(self) -> str:
        if self.nullable:
            return f"{self.java_type} (nullable)"
        return self.java_type


BOOLEAN = DataType(java_type="boolean", nullable=False)
"""Boolean type."""
NULLABLE_BOOLEAN = DataType(java_type="boolean", nullable=True)
"""Nullable boolean type."""
STRING = DataType(java_type="string", nullable=False)
"""String type."""
NULLABLE_STRING = DataType(java_type="string", nullable=True)
"""Nullable string type."""
INT = DataType(java_type="int", nullable=False)
"""Integer type."""
NULLABLE_INT = DataType(java_type="int", nullable=True)
"""Nullable interger type."""
INT_ARRAY = DataType(java_type="int[]", nullable=False)
"""Integer array type."""
NULLABLE_INT_ARRAY = DataType(java_type="int[]", nullable=True)
"""Nullable integer array type."""
LONG = DataType(java_type="long", nullable=False)
"""Long type."""
NULLABLE_LONG = DataType(java_type="long", nullable=True)
"""Nullable long type."""
LONG_ARRAY = DataType(java_type="long[]", nullable=False)
"""Long array type."""
NULLABLE_LONG_ARRAY = DataType(java_type="long[]", nullable=True)
"""Nullable long array type."""
FLOAT = DataType(java_type="float", nullable=False)
"""Float type."""
NULLABLE_FLOAT = DataType(java_type="float", nullable=True)
"""Nullable float type."""
FLOAT_ARRAY = DataType(java_type="float[]", nullable=False)
"""Float array type."""
NULLABLE_FLOAT_ARRAY = DataType(java_type="float[]", nullable=True)
"""Nullable float array type."""
DOUBLE = DataType(java_type="double", nullable=False)
"""Double type."""
NULLABLE_DOUBLE = DataType(java_type="double", nullable=True)
"""Nullable double type."""
DOUBLE_ARRAY = DataType(java_type="double[]", nullable=False)
"""Double array type."""
NULLABLE_DOUBLE_ARRAY = DataType(java_type="double[]", nullable=True)
"""Nullable double array type."""
LOCAL_DATE = DataType(java_type="LocalDate", nullable=False)
"""LocalDate type."""
NULLABLE_LOCAL_DATE = DataType(java_type="LocalDate", nullable=True)
"""Nullable localDate type."""
LOCAL_DATE_TIME = DataType(java_type="LocalDateTime", nullable=False)
"""LocalDateTime type."""
NULLABLE_LOCAL_DATE_TIME = DataType(java_type="LocalDateTime", nullable=True)
"""Nullable localDateTime type."""
ZONED_DATE_TIME = DataType(java_type="ZonedDateTime", nullable=False)
"""ZonedDateTime type."""
NULLABLE_ZONED_DATE_TIME = DataType(java_type="ZonedDateTime", nullable=False)
"""Nullable zonedDateTime type."""
LOCAL_TIME = DataType(java_type="LocalTime", nullable=False)
"""LocalTime type."""
NULLABLE_LOCAL_TIME = DataType(java_type="LocalTime", nullable=True)
"""Nullable localTime type."""
