import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
from pandas.core.indexes.datetimes import DatetimeIndex

from ._file_utils import make_atoti_tempdir
from .type import DataType

_ARROW_TYPES = {
    "boolean": pa.bool_(),
    "double": pa.float64(),
    "float": pa.float32(),
    "long": pa.int64(),
    "int": pa.int32(),
    "double[]": pa.list_(pa.float64()),
    "float[]": pa.list_(pa.float32()),
    "long[]": pa.list_(pa.int64()),
    "int[]": pa.list_(pa.int32()),
    "string": pa.string(),
    "LocalDate": pa.date32(),
    "LocalDateTime": pa.timestamp("s"),
}

_COLUMN_LEVEL_SEPARATOR = "_"

_MIN_INT64 = -sys.maxsize - 1

_SAFE_COLUMN_NAME_PATTERN = re.compile(".*[. ,;{}()\n\t=-].*")


def pandas_to_temporary_parquet(
    dataframe: pd.DataFrame,
    *,
    types: Mapping[str, DataType],
    prefix: Optional[str] = None,
) -> Tuple[Path, Dict[str, str]]:
    tempdir: str = make_atoti_tempdir()
    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=tempdir,
        suffix=".parquet",
        prefix=prefix,
    ) as file:
        dataframe = _clean_index(dataframe)
        dataframe.columns = _flatten_multilevel_columns(dataframe.columns)
        (
            dataframe,
            sanitized_column_name_to_original_column_name,
        ) = _sanitize_column_names(dataframe)

        date_without_time_column_names = _get_date_without_time_column_names(dataframe)

        schema = pa.Schema.from_pandas(dataframe)
        schema = _constrain_schema(
            schema,
            types=types,
            sanitized_column_name_to_original_column_name=sanitized_column_name_to_original_column_name,
        )

        metadata = {
            "_atoti_date_without_time_column_names".encode(): json.dumps(
                date_without_time_column_names
            ).encode(),
            "_atoti_parquet_column_name_to_store_field_name_mapping".encode(): json.dumps(
                sanitized_column_name_to_original_column_name
            ).encode(),
            **schema.metadata,
        }
        dataframe.to_parquet(
            file.name,
            index=False,
            schema=schema.with_metadata(metadata),
        )

        return (
            Path(file.name),
            sanitized_column_name_to_original_column_name,
        )


def _constrain_schema(
    schema: pa.Schema, *, types: Mapping[str, DataType], sanitized_column_name_to_original_column_name: Mapping[str, str]  # type: ignore
) -> pa.Schema:
    """Force the types in the arrow schema with the requested type constraints.

    Additionally, due to differing behavior between Windows and Unix operating systems, if no type is specified for arrays, the largest type is forced.
    This is because the default integer type for Numpy arrays (the underlying data structure used for arrays in a Pandas Dataframe) is C ``long`` (https://docs.scipy.org/doc/numpy-1.10.1/user/basics.types.html).
    On most 64-bit operating systems, this is ``int64``, however on Windows it is represented by ``int32`` (https://docs.microsoft.com/en-us/cpp/c-language/storage-of-basic-types?view=msvc-160).
    Forcing the largest type when none is specified ensures consistent behavior of the Parquet serialization on all operating systems.
    This behavior does not override the type specified by the user if there is one.
    """
    for field_name in schema.names:
        original_field_name = sanitized_column_name_to_original_column_name.get(
            field_name, field_name
        )
        field = schema.field(field_name)
        index = schema.get_field_index(field_name)
        # If the type is set, we force the type in the schema
        if original_field_name in types:
            arrow_type = _ARROW_TYPES.get(types[original_field_name].java_type)
            new_field = pa.field(
                field_name,
                arrow_type if arrow_type is not None else schema.field(index).type,
            )
            schema = schema.set(index, new_field)
        elif field.type == pa.list_(pa.int32()):
            new_field = pa.field(field_name, pa.list_(pa.int64()))
            schema = schema.set(index, new_field)
        elif field.type == pa.list_(pa.float32()):
            new_field = pa.field(field_name, pa.list_(pa.float64()))
            schema = schema.set(index, new_field)
    return schema


def _flatten_multilevel_columns(columns: pd.Index) -> pd.Index:
    return pd.Index(
        (
            _COLUMN_LEVEL_SEPARATOR.join(
                map(str, (level for level in column if not pd.isnull(level)))
            )
            if isinstance(column, tuple)
            else column
            for column in columns.to_flat_index()
        )
    )


def _clean_index(data: pd.DataFrame) -> pd.DataFrame:
    """Un-index the dataframe.

    The named indices are moved to regular columns and the unnamed ones are dropped.
    """
    # Move named columns out of the index.
    dataframe = data.reset_index(
        level=[
            column_name for column_name in data.index.names if column_name is not None
        ],
        drop=False,
    )

    # Get rid of the remaining (unnamed) columns.
    dataframe = dataframe.reset_index(drop=True)

    if dataframe is None:
        raise TypeError("expected dataframe to be defined")

    return dataframe


def _get_date_without_time_column_names(dataframe: pd.DataFrame) -> List[str]:
    return [
        column
        for column in dataframe.columns
        if dataframe[column].dtype == np.dtype("<M8[ns]")
        and _contains_only_dates_without_time(dataframe[column])
    ]


def _contains_only_dates_without_time(values: pd.Series) -> bool:
    # Copied from: https://github.com/pandas-dev/pandas/blob/fd67546153ac6a5685d1c7c4d8582ed1a4c9120f/pandas/io/formats/format.py#L1684
    values = values.ravel()

    values = DatetimeIndex(values)
    if values.tz is not None:
        return False

    values_int = values.asi8
    consider_values = values_int != ...
    final_consider_values = [
        # None types are represented with the minimum 64bit integer in the date index
        int_value != _MIN_INT64 and consider_value
        for int_value, consider_value in zip(values_int, consider_values)
    ]
    one_day_nanos = 86400 * 1e9
    even_days = (
        np.logical_and(
            final_consider_values, values_int % int(one_day_nanos) != 0
        ).sum()
        == 0
    )
    if even_days:
        return True
    return False


def _is_safe_column_name(column_name: str) -> bool:
    return _SAFE_COLUMN_NAME_PATTERN.match(column_name) is None


def _sanitize_column_name(column_name: str) -> str:
    return re.sub("[. ,;{}()\n\t=-]", "_", column_name)


def _sanitize_column_names(
    dataframe: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    original_column_name_to_sanitized_column_name = {
        column_name: _sanitize_column_name(column_name)
        for column_name in dataframe.columns
        if not _is_safe_column_name(column_name)
    }

    dataframe = dataframe.rename(columns=original_column_name_to_sanitized_column_name)
    sanitized_column_name_to_original_column_name = {
        value: key
        for key, value in original_column_name_to_sanitized_column_name.items()
    }

    return dataframe, sanitized_column_name_to_original_column_name
