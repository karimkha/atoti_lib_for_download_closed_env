from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterable, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
from typing_extensions import Literal

from ._docs_utils import (
    CLIENT_SIDE_ENCRYPTION_DOC,
    CSV_KWARGS,
    PARQUET_KWARGS,
    TABLE_CREATION_KWARGS,
    doc,
)
from ._file_utils import split_path_and_pattern
from ._local_session import LocalSession
from ._mappings import EMPTY_MAPPING
from ._pandas_utils import pandas_to_temporary_parquet
from ._path_utils import PathLike, stem_path
from ._plugins import MissingPluginError
from ._scenario_utils import BASE_SCENARIO_NAME
from ._sources.csv import CsvDataSource
from ._sources.parquet import ParquetDataSource
from ._transaction import Transaction
from ._type_utils import typecheck
from .client_side_encryption import ClientSideEncryption
from .config import SessionConfig
from .cube import Cube
from .cubes import Cubes
from .table import Table, _get_client_side_encryption, _LoadParquetPrivateParameters
from .tables import Tables
from .type import DataType

if TYPE_CHECKING:
    # PySpark is only imported for type checking as we don't want it as a dependency
    from pyspark.sql import DataFrame as SparkDataFrame

_CubeCreationMode = Literal[  # pylint: disable=invalid-name
    "auto", "manual", "no_measures"
]


def _infer_table_name(
    *, path: PathLike, pattern: Optional[str], table_name: Optional[str]
) -> str:
    """Infer the name of a table given the path and table_name parameters."""
    if pattern is not None and table_name is None:
        raise ValueError(
            "The table_name parameter is required when the path argument is a glob pattern."
        )
    return table_name or stem_path(path).capitalize()


@dataclass(frozen=True)
class _CreateTablePrivateParameters:
    is_parameter_table: bool = False


@dataclass(frozen=True)
class _ReadParquetPrivateParameters(
    _LoadParquetPrivateParameters, _CreateTablePrivateParameters
):
    _types: Mapping[str, DataType] = EMPTY_MAPPING


class Session(LocalSession[Cubes]):
    """Holds a connection to the Java gateway."""

    def __init__(
        self,
        name: str,
        *,
        config: SessionConfig,
        detached_process: bool,
    ):
        """Create the session and the Java gateway."""
        super().__init__(
            name, config=config, detached_process=detached_process, distributed=False
        )
        self._cubes = Cubes(self)

    def __enter__(self) -> Session:
        """Enter this session's context manager.

        Returns:
            self: to assign it to the "as" keyword.

        """
        return self

    @property
    def cubes(self) -> Cubes:
        """Cubes of the session."""
        return self._cubes

    @property
    def tables(self) -> Tables:  # noqa: D401
        """Tables of the session."""
        return Tables(
            self._java_api,
            {
                table: Table(table, self._java_api)
                for table in self._java_api.get_tables()
            },
        )

    @doc(
        **TABLE_CREATION_KWARGS,
        # Declare the types here because blackdoc and doctest conflict when inlining it in the docstring.
        data_types="""{"Date": tt.type.LOCAL_DATE, "Product": tt.type.STRING, "Quantity": tt.type.NULLABLE_DOUBLE}""",
    )
    def create_table(
        self,
        name: str,
        *,
        types: Mapping[str, DataType],
        keys: Iterable[str] = (),
        partitioning: Optional[str] = None,
        hierarchized_columns: Optional[Iterable[str]] = None,
        **kwargs: Any,
    ) -> Table:
        """Create a table from a schema.

        Args:
            name: The name of the table to create.
            types: Types for all columns of the table.
                This defines the columns which will be expected in any future data loaded into the table.
            {keys}
            {partitioning}
            {hierarchized_columns}

        Example:

            >>> from datetime import date
            >>> table = session.create_table(
            ...     "Product",
            ...     types={data_types},
            ...     keys=["Date"],
            ... )
            >>> table.head()
            Empty DataFrame
            Columns: [Product, Quantity]
            Index: []
            >>> table.append((date(2021, 5, 19), "TV", 15.0))
            >>> table.head()
                       Product  Quantity
            Date
            2021-05-19      TV      15.0

        """
        private_parameters = _CreateTablePrivateParameters(**kwargs)
        self._java_api.create_table(
            name,
            types=types,
            keys=keys,
            partitioning=partitioning,
            hierarchized_columns=hierarchized_columns,
            is_parameter_table=private_parameters.is_parameter_table,
        )
        return Table(name, self._java_api)

    @doc(**TABLE_CREATION_KWARGS)
    def read_pandas(
        self,
        dataframe: pd.DataFrame,
        *,
        table_name: str,
        keys: Iterable[str] = (),
        partitioning: Optional[str] = None,
        types: Mapping[str, DataType] = EMPTY_MAPPING,
        hierarchized_columns: Optional[Iterable[str]] = None,
        **kwargs: Any,
    ) -> Table:
        """Read a pandas DataFrame into a table.

        All the named indices of the DataFrame are included into the table.
        Multilevel columns are flattened into a single string name.

        Args:
            dataframe: The DataFrame to load.
            {table_name}
            {keys}
            {partitioning}
            types: Types for some or all columns of the table.
                Types for non specified columns will be inferred from pandas dtypes.
            {hierarchized_columns}

        Returns:
            The created table holding the content of the DataFrame.
        """
        (
            parquet_path,
            parquet_column_name_to_table_column_name,
        ) = pandas_to_temporary_parquet(dataframe, prefix=table_name, types=types)
        return self.read_parquet(
            parquet_path,
            keys=keys,
            table_name=table_name,
            partitioning=partitioning,
            hierarchized_columns=hierarchized_columns,
            _parquet_column_name_to_table_column_name=parquet_column_name_to_table_column_name,
            _types=types,
            _is_temporary_file=True,
            **kwargs,
        )

    @doc(**TABLE_CREATION_KWARGS)
    @typecheck(ignored_params=["dataframe"])
    def read_spark(
        self,
        dataframe: SparkDataFrame,
        *,
        table_name: str,
        keys: Iterable[str] = (),
        partitioning: Optional[str] = None,
        hierarchized_columns: Optional[Iterable[str]] = None,
        **kwargs: Any,
    ) -> Table:
        """Read a Spark DataFrame into a table.

        Args:
            dataframe: The DataFrame to load.
            {table_name}
            {keys}
            {partitioning}
            {hierarchized_columns}

        Returns:
            The created table holding the content of the DataFrame.
        """
        from ._spark_utils import spark_to_temporary_parquet

        # Create a Parquet and read it
        file_name = spark_to_temporary_parquet(dataframe, table_name)
        return self.read_parquet(
            path=file_name,
            keys=keys,
            table_name=table_name,
            partitioning=partitioning,
            hierarchized_columns=hierarchized_columns,
            _is_temporary_file=True,
            **kwargs,
        )

    @doc(**{**TABLE_CREATION_KWARGS, **CSV_KWARGS, **CLIENT_SIDE_ENCRYPTION_DOC})
    def read_csv(
        self,
        path: PathLike,
        *,
        keys: Iterable[str] = (),
        table_name: Optional[str] = None,
        separator: Optional[str] = None,
        encoding: str = "utf-8",
        process_quotes: Optional[bool] = None,
        partitioning: Optional[str] = None,
        types: Mapping[str, DataType] = EMPTY_MAPPING,
        array_separator: Optional[str] = None,
        hierarchized_columns: Optional[Iterable[str]] = None,
        date_patterns: Mapping[str, str] = EMPTY_MAPPING,
        client_side_encryption: Optional[ClientSideEncryption] = None,
        **kwargs: Any,
    ) -> Table:
        """Read a CSV file into a table.

        Args:
            {path}
            {keys}
            table_name: The name of the table to create.
                Required when *path* is a glob pattern.
                Otherwise, defaults to the final component of the *path* argument.
            {separator}
            {encoding}
            {process_quotes}
            {partitioning}
            types: Types for some or all columns of the table.
                Types for non specified columns will be inferred from the first 1,000 lines.
            {array_separator}
            {hierarchized_columns}
            {date_patterns}
            {client_side_encryption}

        Returns:
            The created table holding the content of the CSV file(s).
        """
        private_parameters = _CreateTablePrivateParameters(**kwargs)
        full_path = path
        path, pattern = split_path_and_pattern(path, ".csv")

        table_name = _infer_table_name(
            path=path, pattern=pattern, table_name=table_name
        )

        csv_file_format = CsvDataSource(self._java_api).discover_file_format(
            path=path,
            keys=keys,
            separator=separator,
            encoding=encoding,
            process_quotes=process_quotes,
            array_separator=array_separator,
            pattern=pattern,
            date_patterns=date_patterns,
            client_side_encryption=_get_client_side_encryption(
                client_side_encryption, java_api=self._java_api
            ),
        )
        types = (
            {**csv_file_format.types, **types}
            if types is not None
            else csv_file_format.types
        )
        process_quotes = (
            process_quotes
            if process_quotes is not None
            else csv_file_format.process_quotes
        )
        separator = separator if separator is not None else csv_file_format.separator
        date_patterns = (
            {**csv_file_format.date_patterns, **date_patterns}
            if date_patterns is not None
            else csv_file_format.date_patterns
        )
        table = self.create_table(
            table_name,
            types=types,
            keys=keys,
            partitioning=partitioning,
            hierarchized_columns=hierarchized_columns,
            is_parameter_table=private_parameters.is_parameter_table,
        )
        table.load_csv(
            full_path,
            separator=separator,
            encoding=encoding,
            process_quotes=process_quotes,
            array_separator=array_separator,
            date_patterns=date_patterns,
            client_side_encryption=client_side_encryption,
        )
        return table

    @doc(**{**TABLE_CREATION_KWARGS, **PARQUET_KWARGS, **CLIENT_SIDE_ENCRYPTION_DOC})
    def read_parquet(
        self,
        path: PathLike,
        *,
        keys: Iterable[str] = (),
        table_name: Optional[str] = None,
        partitioning: Optional[str] = None,
        hierarchized_columns: Optional[Iterable[str]] = None,
        client_side_encryption: Optional[ClientSideEncryption] = None,
        **kwargs: Any,
    ) -> Table:
        """Read a Parquet file into a table.

        Args:
            {path}
            {keys}
            table_name: The name of the table to create.
                Required when *path* is a glob pattern.
                Otherwise, defaults to the final component of the *path* argument.
            {partitioning}
            {hierarchized_columns}
            {client_side_encryption}

        Returns:
            The created table holding the content of the Parquet file(s).
        """
        private_parameters = _ReadParquetPrivateParameters(**kwargs)
        full_path = path
        path, pattern = split_path_and_pattern(path, ".parquet")
        table_name = _infer_table_name(
            path=path, pattern=pattern, table_name=table_name
        )

        inferred_types = ParquetDataSource(self._java_api).infer_parquet_types(
            path=path,
            keys=keys,
            pattern=pattern,
            _parquet_column_name_to_table_column_name=private_parameters._parquet_column_name_to_table_column_name,
            client_side_encryption=_get_client_side_encryption(
                client_side_encryption, java_api=self._java_api
            ),
        )
        types = {**inferred_types, **private_parameters._types}

        table = self.create_table(
            table_name,
            types=types,
            keys=keys,
            partitioning=partitioning,
            hierarchized_columns=hierarchized_columns,
            is_parameter_table=private_parameters.is_parameter_table,
        )
        table.load_parquet(
            full_path,
            _parquet_column_name_to_table_column_name=private_parameters._parquet_column_name_to_table_column_name,
            client_side_encryption=client_side_encryption,
            _is_temporary_file=private_parameters._is_temporary_file,
        )
        return table

    @doc(**TABLE_CREATION_KWARGS)
    def read_numpy(
        self,
        array: np.ndarray,  # type: ignore
        *,
        columns: Sequence[str],
        table_name: str,
        keys: Iterable[str] = (),
        partitioning: Optional[str] = None,
        types: Mapping[str, DataType] = EMPTY_MAPPING,
        hierarchized_columns: Optional[Iterable[str]] = None,
        **kwargs: Any,
    ) -> Table:
        """Read a NumPy 2D array into a new table.

        Args:
            array: The NumPy 2D ndarray to read the data from.
            columns: The names to use for the table's columns.
                They must be in the same order as the values in the NumPy array.
            {table_name}
            {keys}
            {partitioning}
            types: Types for some or all columns of the table.
                Types for non specified columns will be inferred from numpy data types.
            {hierarchized_columns}

        Returns:
            The created table holding the content of the array.
        """
        dataframe = pd.DataFrame(array, columns=columns)
        return self.read_pandas(
            dataframe,
            table_name=table_name,
            keys=keys,
            partitioning=partitioning,
            types=types,
            hierarchized_columns=hierarchized_columns,
            **kwargs,
        )

    def read_sql(self, *args: Any, **kwargs: Any) -> Any:  # pylint: disable=no-self-use
        raise MissingPluginError("sql")

    def start_transaction(self, scenario_name: str = BASE_SCENARIO_NAME) -> Transaction:
        """Start a transaction to batch several table operations.

        * It is more efficient than doing each table operation one after the other.
        * It avoids possibly incorrect intermediate states (e.g. if loading some new data requires dropping existing rows first).

        .. note::
            Some operations are not allowed during a transaction:

            * Long-running operations such as :meth:`~atoti.table.Table.load_kafka`.
            * Operations changing the structure of the session's tables such as :meth:`~atoti.table.Table.join` or :meth:`~atoti.session.Session.read_parquet`.
            * Operations not related to data loading or dropping such as defining a new measure.
            * Operations on parameter tables created from :meth:`~atoti.cube.Cube.create_parameter_hierarchy_from_members` and :meth:`~atoti.cube.Cube.create_parameter_simulation`.
            * Operations on other source scenarios than the one the transaction is started on.

        Args:
            scenario_name: The name of the source scenario impacted by all the table operations inside the transaction.

        Example:
            >>> df = pd.DataFrame(
            ...     columns=["City", "Price"],
            ...     data=[
            ...         ("Berlin", 150.0),
            ...         ("London", 240.0),
            ...         ("New York", 270.0),
            ...         ("Paris", 200.0),
            ...     ],
            ... )
            >>> table = session.read_pandas(
            ...     df, keys=["City"], table_name="start_transaction example"
            ... )
            >>> cube = session.create_cube(table)
            >>> extra_df = pd.DataFrame(
            ...     columns=["City", "Price"],
            ...     data=[
            ...         ("Singapore", 250.0),
            ...     ],
            ... )
            >>> with session.start_transaction():
            ...     table += ("New York", 100.0)
            ...     table.drop({"City": "Paris"})
            ...     table.load_pandas(extra_df)
            ...
            >>> table.head().sort_index()
                       Price
            City
            Berlin     150.0
            London     240.0
            New York   100.0
            Singapore  250.0

        """
        return Transaction(self._java_api, scenario_name)

    def create_cube(
        self,
        base_table: Table,
        name: Optional[str] = None,
        *,
        mode: _CubeCreationMode = "auto",
    ) -> Cube:
        """Create a cube based on the passed table.

        Args:
            base_table: The base table of the cube.
            name: The name of the created cube.
                Defaults to the name of the base table.
            mode: The cube creation mode:

                * ``auto``: Creates hierarchies for every key column or non-numeric column of the table, and measures for every numeric column.
                * ``manual``: Does not create any hierarchy or measure (except from the count).
                * ``no_measures``: Creates the hierarchies like ``auto`` but does not create any measures.

                For tables with ``hierarchized_columns`` specified, these will be converted into
                hierarchies regardless of the cube creation mode.

        Example:
            >>> table = session.create_table(
            ...     "Table",
            ...     types={"id": tt.type.STRING, "value": tt.type.NULLABLE_DOUBLE},
            ... )
            >>> cube_auto = session.create_cube(table)
            >>> sorted(list(cube_auto.measures.keys()))
            ['contributors.COUNT', 'update.TIMESTAMP', 'value.MEAN', 'value.SUM']
            >>> list(cube_auto.hierarchies.keys())
            [('Table', 'id')]
            >>> cube_no_measures = session.create_cube(table, mode="no_measures")
            >>> sorted(list(cube_no_measures.measures.keys()))
            ['contributors.COUNT', 'update.TIMESTAMP']
            >>> list(cube_no_measures.hierarchies.keys())
            [('Table', 'id')]
            >>> cube_manual = session.create_cube(table, mode="manual")
            >>> sorted(list(cube_manual.measures.keys()))
            ['contributors.COUNT', 'update.TIMESTAMP']
            >>> list(cube_manual.hierarchies.keys())
            []

        See Also:
            Hierarchies and measures created by a :meth:`~atoti.table.Table.join`.
        """
        if name is None:
            name = base_table.name

        self._java_api.create_cube_from_table(
            table=base_table, cube_name=name, creation_mode=mode.upper()
        )
        self._java_api.refresh()
        Cube(java_api=self._java_api, name=name, base_table=base_table, session=self)

        return self.cubes[name]

    def create_scenario(self, name: str, *, origin: str = BASE_SCENARIO_NAME) -> None:
        """Create a new source scenario.

        Args:
            name: The name of the scenario.
            origin: The scenario to fork.
        """
        self._java_api.create_scenario(name, origin)

    def delete_scenario(self, scenario: str) -> None:
        """Delete the source scenario with the provided name if it exists."""
        if scenario == BASE_SCENARIO_NAME:
            raise ValueError("Cannot delete the base scenario")
        self._java_api.delete_scenario(scenario)

    @property
    def scenarios(self) -> Sequence[str]:  # noqa: D401
        """Collection of source scenarios of the session."""
        return self._java_api.get_scenarios()

    def export_translations_template(self, path: PathLike) -> None:
        """Export a template containing all translatable values in the session's cubes.

        Args:
            path: The path at which to write the template.
        """
        self._java_api.export_i18n_template(path)

    def _retrieve_cube(self, cube_name: str) -> Cube:
        java_cube = self._java_api.retrieve_cube(cube_name)
        return Cube(
            java_api=self._java_api,
            name=java_cube.getName(),
            base_table=self.tables[java_cube.getStoreName()],
            session=self,
        )

    def _retrieve_cubes(self) -> Dict[str, Cube]:
        return {
            java_cube.getName(): Cube(
                java_api=self._java_api,
                name=java_cube.getName(),
                base_table=self.tables[java_cube.getStoreName()],
                session=self,
            )
            for java_cube in self._java_api.retrieve_cubes()
        }
