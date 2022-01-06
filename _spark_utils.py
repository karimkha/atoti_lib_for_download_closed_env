from __future__ import annotations

import random
import string
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Mapping, Optional

from ._file_utils import make_atoti_tempdir

if TYPE_CHECKING:
    # Spark is only imported for type checking as we don't want it as a dependency
    from pyspark.sql import DataFrame, SparkSession

_SPARK_PROPERTIES = {"spark.sql.parquet.outputTimestampType": "TIMESTAMP_MICROS"}


# No type stubs for spark, so we ignore this error
def spark_to_temporary_parquet(
    dataframe: DataFrame,  # type: ignore
    name: Optional[str] = None,
) -> Path:
    """Convert a Spark DataFrame to a temporary Parquet file in a temporary folder.

    Args:
        dataframe: The DataFrame to write.
        name: Name to use in the temporary folder where the file is written.

    Returns:
        The path to the temporary file.
    """
    spark = dataframe.sql_ctx.sparkSession
    # Modify output format of timestamp columns
    # https://github.com/apache/spark/blob/7281784883d6bacf3d024397fd90edf65c06e02b/sql/catalyst/src/main/scala/org/apache/spark/sql/internal/SQLConf.scala#L399
    previous_props = _set_properties(spark, _SPARK_PROPERTIES)
    folder_path = _get_random_temp_folder(name)
    dataframe.write.parquet(str(folder_path.absolute()))
    _set_properties(spark, previous_props)
    return folder_path


def _set_properties(
    spark: SparkSession,  # type: ignore
    props: Mapping[str, str],
) -> Dict[str, str]:
    """Set the given properties to the session and return the previous ones.

    Args:
        spark: The Spark session.
        props: The properties to set.

    Returns:
        The previous values of the changed properties.
    """
    previous = {}
    for prop, value in props.items():
        previous[prop] = spark.conf.get(prop, default=None)
        if value is None:
            spark.conf.unset(prop)
        else:
            spark.conf.set(prop, value)
    return previous


def _get_random_temp_folder(name: Optional[str] = None) -> Path:
    """Get a random folder path.

    Args:
        name : Name to include in the path.

    Returns:
        The path to the folder.
    """
    tempdir = Path(make_atoti_tempdir())
    if name is None:
        name = "spark_dataframe"
    random_name = (
        name
        + "_"
        + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    )
    return tempdir / random_name
