from __future__ import annotations

import re
from dataclasses import dataclass
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

import pandas as pd
from py4j.clientserver import ClientServer, JavaParameters, PythonParameters
from py4j.java_collections import ListConverter
from typing_extensions import Literal

from ._endpoint import EndpointHandler
from ._measures.utils import convert_level_in_description
from ._plugins import MissingPluginError
from ._providers import PartialAggregateProvider
from ._py4j_utils import (
    to_java_map,
    to_java_object_array,
    to_java_object_list,
    to_java_string_array,
    to_python_dict,
    to_python_list,
)
from ._query_plan import QueryAnalysis, QueryPlan, RetrievalData
from ._sources.csv import CsvFileFormat
from ._type_utils import is_array, is_temporal
from .client_side_encryption import ClientSideEncryption
from .comparator import ASCENDING, Comparator
from .config import SessionConfig
from .config._utils import serialize_config_to_json
from .exceptions import _java_api_call_wrapper
from .hierarchy import Hierarchy
from .level import Level
from .report import LoadingReport, _warn_new_errors
from .type import DataType

if TYPE_CHECKING:
    from ._local_cube import LocalCube
    from .cube import Cube
    from .measure import Measure
    from .measure_description import MeasureDescription
    from .table import Table


def _parse_detailed_type(underlying_type: str) -> DataType:
    """Parse java detailed type string in DataType."""
    clean_type = underlying_type.replace("nullable ", "")
    clean_type = clean_type.split("[")[0]
    java_type_string = (
        clean_type
        if clean_type not in ["Boolean", "String"]
        # .lower() since java detailed type sometimes start with Upper or Lower case.
        else clean_type.lower()
    )
    nullable = "nullable" in underlying_type
    array = "[]" in underlying_type
    return DataType(
        java_type=java_type_string + "[]" if array else java_type_string,  # type: ignore
        nullable=nullable,
    )


class ApiMetaClass(type):
    """Meta class for the API calls."""

    def __new__(  # pylint: disable=too-many-positional-parameters
        cls, classname: str, bases: Tuple[type, ...], class_dict: Mapping[str, Any]
    ) -> ApiMetaClass:
        """Automatically wrap all of the classes methods.

        This class applies the api_call_wrapper to all of a particular classes methods.
        This allows for cleaner handling of Py4J related exceptions.
        """
        new_class_dict = {}
        for attribute_name, attribute in class_dict.items():
            if isinstance(attribute, FunctionType):
                attribute = _java_api_call_wrapper(attribute)
            new_class_dict[attribute_name] = attribute
        return type.__new__(cls, classname, bases, new_class_dict)


# pylint: disable=too-many-lines
class JavaApi(metaclass=ApiMetaClass):
    """API for communicating with the JVM."""

    _client_side_encryption: Optional[ClientSideEncryption] = None

    def __init__(
        self, *, py4j_java_port: Optional[int] = None, distributed: bool = False
    ):
        """Create the Java gateway."""
        self.gateway: Any = JavaApi._create_py4j_gateway(py4j_java_port)
        self.java_session: Any = self.gateway.entry_point
        self.java_session.api(distributed)

    @property
    def java_api(self) -> Any:
        return self.java_session.api()

    @staticmethod
    def _create_py4j_gateway(java_port: Optional[int] = None) -> ClientServer:
        # Connect to the Java side using the provided Java port
        # and start the Python callback server with a dynamic port.
        gateway = ClientServer(
            java_parameters=JavaParameters(port=java_port),
            python_parameters=PythonParameters(daemonize=True, port=0),
        )

        # Retrieve the port on which the python callback server was bound to.
        cb_server = gateway.get_callback_server()
        if cb_server is None:
            raise ValueError("Null callback server from py4j gateway")
        python_port = cb_server.get_listening_port()

        # Tell the Java side to connect to the Python callback server with the new Python port.
        gateway_server = gateway.java_gateway_server
        if gateway_server is None:
            raise ValueError("Null gateway server from py4j gateway")
        # ignore type next line because we do some Java calls
        gateway_server.resetCallbackClient(
            gateway_server.getCallbackClient().getAddress(), python_port  # type: ignore
        )

        return gateway

    def shutdown(self) -> None:
        """Shutdown the connection to the Java gateway."""
        self.gateway.shutdown()

    def refresh(self) -> None:
        """Refresh the Java session."""
        self.java_api.refresh()
        _warn_new_errors(self.get_new_load_errors())

    def publish_measures(self, cube_name: str) -> None:
        """Publish the new measures."""
        self.java_api.outsideTransactionApi().publishMeasures(cube_name)

    def clear_session(self) -> None:
        """Refresh the pivot."""
        self.java_api.clearSession()

    def get_session_port(self) -> int:
        """Return the port of the session."""
        return self.java_session.getPort()

    def get_throwable_root_cause(self, throwable: Any) -> str:
        """Get the root cause of a java exception."""
        return self.java_api.getRootCause(throwable)

    def generate_jwt(self) -> str:
        """Return the JWT required to authenticate against to this session."""
        return self.java_session.generateJwt()

    def create_endpoint(
        self,
        *,
        http_method: Literal["POST", "GET", "PUT", "DELETE"],
        route: str,
        handler: EndpointHandler,
    ) -> None:
        """Create a new custom endpoint."""
        self.java_api.outsideTransactionApi().createEndpoint(
            http_method,
            route,
            handler,
        )

    def configure_session(self, config: SessionConfig) -> None:
        json_config = serialize_config_to_json(config)
        self.java_api.configureSession(json_config)

    def delete_role(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def upsert_role(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def get_roles(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def get_role_mapping(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def upsert_role_mapping(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def remove_role_from_role_mapping(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def set_locale(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> None:
        """Set the locale to use for the session."""
        raise MissingPluginError("plus")

    def export_i18n_template(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        """Generate a template translations file at the desired location."""
        raise MissingPluginError("plus")

    def start_application(self) -> None:
        """Start the application."""
        self.java_api.startSession()

    def _create_java_types(self, types: Mapping[str, DataType]) -> Any:
        """Convert the python types to java types."""
        # pylint: disable=invalid-name
        JavaColumnType: Any = self.gateway.jvm.io.atoti.loading.impl.TypeImpl  # type: ignore
        # pylint: enable=invalid-name
        converted = {
            field: JavaColumnType(type_value.java_type, type_value.nullable)
            for (field, type_value) in types.items()
        }
        return to_java_map(converted, gateway=self.gateway)

    def _create_java_types_list(self, types: Iterable[DataType]) -> Any:
        """Convert list of python types to java types."""
        converted = [self._get_java_type(type_value) for type_value in types]
        return to_java_object_list(converted, gateway=self.gateway)

    def _get_java_type(self, data_type: DataType) -> Any:
        """Convert a python type to a java one."""
        # pylint: disable=invalid-name
        atoti_package = self.gateway.jvm.io.atoti  # type: ignore
        JavaColumnType: Any = atoti_package.loading.impl.TypeImpl  # type: ignore
        # pylint: enable=invalid-name
        return JavaColumnType(data_type.java_type, data_type.nullable)

    def get_tables(self) -> List[str]:
        """List all the tables of the session."""
        return to_python_list(self.java_api.getStores())

    def create_table_params(
        self,
        *,
        keys: Iterable[str],
        partitioning: Optional[str],
        types: Mapping[str, DataType],
        hierarchized_columns: Optional[Iterable[str]] = None,
        is_parameter_table: bool,
    ) -> Any:
        """Create the table parameters."""
        java_keys = ListConverter().convert(keys, self.gateway._gateway_client)
        java_types = self._create_java_types(types)
        java_hierarchized_columns = (
            ListConverter().convert(hierarchized_columns, self.gateway._gateway_client)
            if hierarchized_columns is not None
            else None
        )
        package: Any = self.gateway.jvm.io.atoti.loading.impl  # type: ignore
        params = package.StoreParams(
            java_keys,
            partitioning,
            java_types,
            java_hierarchized_columns,
            is_parameter_table,
        )
        return params

    def create_loading_params(
        self,
        *,
        scenario_name: Optional[str],
    ) -> Any:
        """Create the loading parameters."""
        package: Any = self.gateway.jvm.io.atoti.loading.impl  # type: ignore
        params = package.LoadingParams()
        if scenario_name is not None:
            params.setBranch(scenario_name)
        return params

    def create_table(
        self,
        name: str,
        *,
        types: Mapping[str, DataType],
        keys: Iterable[str],
        partitioning: Optional[str],
        hierarchized_columns: Optional[Iterable[str]],
        is_parameter_table: bool,
    ) -> None:
        """Create a java store from its schema."""
        table_params = self.create_table_params(
            keys=keys,
            partitioning=partitioning,
            types=types,
            hierarchized_columns=hierarchized_columns,
            is_parameter_table=is_parameter_table,
        )
        self.java_api.outsideTransactionApi().createStore(name, table_params)

    def convert_source_params(self, params: Mapping[str, Any]) -> Any:
        """Convert the params to Java Objects."""
        java_params = {}
        for param in params:
            value = params[param]
            if isinstance(value, Mapping):
                value = to_java_map(value, gateway=self.gateway)
            elif isinstance(value, Iterable) and not isinstance(value, str):
                value = to_java_object_list(value, gateway=self.gateway)
            java_params[param] = value
        return to_java_map(java_params, gateway=self.gateway)

    def discover_csv_file_format(
        self,
        *,
        keys: Iterable[str],
        source_params: Mapping[str, Any],
    ) -> CsvFileFormat:
        source_params = self.convert_source_params(source_params)
        types = {}
        date_patterns = {}
        java_csv_format = self.java_api.outsideTransactionApi().discoverCsvFileFormat(
            to_java_object_list(keys, gateway=self.gateway),
            source_params,
        )
        for column_name, java_type in to_python_dict(
            java_csv_format.getTypes()
        ).items():
            data_type = DataType(
                java_type=java_type.getJavaType(),
                nullable=java_type.nullable(),
            )
            types[column_name] = data_type
            if is_temporal(data_type):
                match = re.match(
                    r"^[a-zA-Z]+\[(?P<pattern>.*)\]$",
                    java_type.literalType().getParser(),
                )
                if match is None:
                    raise ValueError("Failed to parse date pattern.")
                date_patterns[column_name] = match.group("pattern")

        file_format = CsvFileFormat(
            java_csv_format.shouldProcessQuotes(),
            java_csv_format.getSeparator(),
            types,
            date_patterns,
        )
        return file_format

    def infer_table_types_from_source(
        self,
        *,
        source_key: str,
        keys: Iterable[str],
        source_params: Mapping[str, Any],
    ) -> Dict[str, DataType]:
        """Infer Table types from a data source."""
        source_params = self.convert_source_params(source_params)
        types = {}
        for column_name, java_type in to_python_dict(
            self.java_api.outsideTransactionApi().inferTypesFromDataSource(
                source_key,
                to_java_object_list(keys, gateway=self.gateway),
                source_params,
            )
        ).items():
            types[column_name] = DataType(
                java_type=java_type.getJavaType(),
                nullable=java_type.nullable(),
            )
        return types

    def load_data_into_table(
        self,
        table_name: str,
        *,
        source_key: str,
        scenario_name: Optional[str],
        source_params: Mapping[str, Any],
    ) -> None:
        """Load the data into an existing table with a given source."""
        load_params = self.create_loading_params(scenario_name=scenario_name)
        source_params = self.convert_source_params(source_params)
        self.java_api.loadDataSourceIntoStore(
            table_name, source_key, load_params, source_params
        )
        # Check if errors happened during the loading
        _warn_new_errors(self.get_new_load_errors())

    def create_scenario(self, scenario_name: str, parent_scenario: str) -> None:
        """Create a new scenario on the table."""
        self.java_api.outsideTransactionApi().createBranch(
            scenario_name, parent_scenario
        )

    def get_scenarios(self) -> List[str]:
        """Get the list of scenarios defined in the current session."""
        return to_python_list(self.java_api.getBranches())

    def delete_scenario(self, scenario: str) -> None:
        """Delete a scenario from the table."""
        self.java_api.outsideTransactionApi().deleteBranch(scenario)

    def start_transaction(self, scenario_name: str) -> None:
        """Start a multi operation transaction on the datastore."""
        self.java_api.startTransaction(scenario_name)

    def end_transaction(self, has_succeeded: bool) -> None:
        """End a multi operation transaction on the datastore."""
        self.java_api.endTransaction(has_succeeded)

    @dataclass(frozen=True)
    class AggregatesCacheDescription:
        """Aggregates cache description."""

        capacity: int

    def get_aggregates_cache_description(
        self, cube: LocalCube[Any, Any, Any]
    ) -> JavaApi.AggregatesCacheDescription:
        """Return the description of the aggregates cache associated with a given cube."""
        jcache_desc = (
            self.java_api.outsideTransactionApi().getAggregatesCacheDescription(
                cube.name
            )
        )
        return JavaApi.AggregatesCacheDescription(capacity=jcache_desc.getSize())

    def set_aggregates_cache(
        self, cube: LocalCube[Any, Any, Any], capacity: int
    ) -> None:
        """Set the aggregates cache description for a given cube."""
        self.java_api.outsideTransactionApi().setAggregatesCache(cube.name, capacity)

    def _convert_partial_provider(self, provider: PartialAggregateProvider) -> Any:
        """Convert the partial provider to the Java Object."""
        levels = ListConverter().convert(
            [level._java_description for level in provider.levels],
            self.gateway._gateway_client,
        )
        measures = ListConverter().convert(
            [measure.name for measure in provider.measures],
            self.gateway._gateway_client,
        )
        java_class: Any = self.gateway.jvm.io.atoti.api.impl.PythonPartialProvider  # type: ignore
        return java_class(provider.key, levels, measures)

    def get_aggregate_providers(self, cube: Cube) -> List[PartialAggregateProvider]:
        """Get the partial aggregates providers."""
        java_providers = (
            self.java_api.outsideTransactionApi().getPartialAggregateProviders(
                cube.name
            )
        )
        return [
            PartialAggregateProvider(
                provider.getKey(),
                [
                    cube._get_level_from_identifier(level)
                    for level in to_python_list(provider.getLevels())
                ],
                [
                    cube.measures[measure_name]
                    for measure_name in to_python_list(provider.getMeasures())
                ],
            )
            for provider in to_python_list(java_providers)
        ]

    def set_aggregate_providers(
        self,
        cube: Cube,
        providers: Iterable[PartialAggregateProvider],
    ) -> None:
        """Set the partial aggregate providers."""
        java_providers = ListConverter().convert(
            [self._convert_partial_provider(provider) for provider in providers],
            self.gateway._gateway_client,
        )
        self.java_api.outsideTransactionApi().setPartialAggregateProviders(
            cube.name, java_providers
        )

    def join_distributed_cluster(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        """Join the distributed cluster at the given address for the given distributed cube."""
        raise MissingPluginError("plus")

    @dataclass(frozen=True)
    class ColumnDescription:
        """Table column description."""

        name: str
        data_type: DataType

    # https://github.com/Microsoft/pyright/issues/104 -> Unbound variables not detected
    def get_table_schema(self, table: Table) -> List[JavaApi.ColumnDescription]:  # type: ignore
        """Return the schema of the java table."""
        schema = self.java_api.getStoreSchema(table.name)
        columns_descriptions = []
        for i in range(0, len(list(schema.fieldNames()))):
            columns_descriptions.append(
                JavaApi.ColumnDescription(
                    name=schema.fieldNames()[i],
                    data_type=DataType(
                        java_type=schema.types()[i].getJavaType(),
                        nullable=schema.types()[i].nullable(),
                    ),
                )
            )
        return columns_descriptions

    def get_table_partitioning(self, table: Table) -> str:
        """Return the table's partitioning."""
        return self.java_api.outsideTransactionApi().getStorePartitioning(table.name)

    @staticmethod
    def _convert_reports(reports: Any) -> List[LoadingReport]:
        """Convert the Java report to Python ones."""
        return [
            LoadingReport(
                r.getName(),
                r.getType(),
                r.getLoadedCount(),
                r.getErrorCount(),
                r.getDuration(),
                to_python_list(r.getFailureMessages()),
            )
            for r in to_python_list(reports)
        ]

    def get_loading_report(self, table: Table) -> List[LoadingReport]:
        """Return the loading report of the table."""
        reports = self.java_api.getLoadingReports(table.name)
        return self._convert_reports(reports)

    def get_new_load_errors(self) -> Dict[str, int]:
        """Return the new loading errors per table."""
        errors = self.java_api.getNewLoadingErrors()
        return to_python_dict(errors)

    def get_key_columns(self, table: Table) -> List[str]:
        """Return the list of key columns for the table."""
        java_columns = self.java_api.outsideTransactionApi().getKeyFields(table.name)
        return to_python_list(java_columns)

    def get_selection_fields(self, cube: Cube) -> List[str]:
        """Return the list of fields that are part of the cube's datastore selection."""
        java_fields = self.java_api.outsideTransactionApi().getSelectionFields(
            cube.name
        )
        return to_python_list(java_fields)

    def create_cube_from_table(
        self,
        *,
        table: Table,
        cube_name: str,
        creation_mode: str,
    ) -> None:
        """Create a cube from a given table."""
        self.java_api.outsideTransactionApi().createCubeFromStore(
            table.name, cube_name, creation_mode
        )

    def create_distributed_cube(self, cube_name: str) -> None:
        """Create a distributed cube."""
        self.java_api.createDistributedCube(cube_name)

    def generate_cube_schema_image(self, cube_name: str) -> str:
        """Generate the cube schema image and return its path."""
        return self.java_api.outsideTransactionApi().getCubeSchemaPath(cube_name)

    def generate_datastore_schema_image(self) -> str:
        """Generate the datastore schema image and return its path."""
        return self.java_api.outsideTransactionApi().getDatastoreSchemaPath()

    def delete_cube(self, cube_name: str) -> None:
        """Delete a cube from the current session."""
        self.java_api.outsideTransactionApi().deleteCube(cube_name)

    def create_join(
        self,
        table: Table,
        other_table: Table,
        *,
        mapping: Optional[Mapping[str, str]],
    ) -> None:
        """Define a join between two tables."""
        jmapping = (
            to_java_map(mapping, gateway=self.gateway) if mapping is not None else None
        )

        self.java_api.outsideTransactionApi().createReferences(
            table.name, other_table.name, jmapping
        )

    def get_table_size(self, table: Table) -> int:
        """Get the size of the table on its current scenario."""
        return self.java_api.outsideTransactionApi().getStoreSize(
            table.name, table.scenario
        )

    def delete_rows_from_table(
        self,
        *,
        table: Table,
        scenario_name: str,
        coordinates: Iterable[Mapping[str, Any]],
    ) -> None:
        """Delete rows from the table matching the provided coordinates."""
        jcoordinates_list: Any = None
        if coordinates:
            jcoordinates = [
                to_java_map(column_values, gateway=self.gateway)
                for column_values in coordinates
            ]
            jcoordinates_list = ListConverter().convert(
                jcoordinates, self.gateway._gateway_client
            )
        self.java_api.deleteOnStoreBranch(table.name, scenario_name, jcoordinates_list)

    def get_table_dataframe(
        self,
        table: Table,
        rows: int,
        *,
        keys: Iterable[str],
        scenario_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return the first given rows of the table as a pandas DataFrame."""
        dfrh = self.java_api.outsideTransactionApi().dataFrameRowsAndHeaders(
            table.name, scenario_name, rows
        )

        headers = to_python_list(dfrh.getContentHeader())
        content = to_python_list(dfrh.getContentRows())
        dataframe = cast(
            pd.DataFrame,
            pd.DataFrame(data=content, columns=headers).apply(
                pd.to_numeric, errors="ignore"
            ),
        )

        for name, data_type in table._types.items():
            if is_temporal(data_type):
                dataframe[name] = dataframe[name].apply(to_date)
            if is_array(data_type):
                dataframe[name] = dataframe[name].apply(to_python_list)

        if keys:
            dataframe.set_index(keys, inplace=True)

        return dataframe

    @staticmethod
    def _convert_from_java_levels(jlevels: Any) -> Dict[str, Level]:
        """Convert from java levels."""
        jlevels_dict = to_python_dict(jlevels)
        levels = {}
        for (name, jlvl) in jlevels_dict.items():
            comparator_name = jlvl.getPythonExposedComparatorKey()
            first_members = (
                list(jlvl.getFirstMembers())
                if jlvl.getFirstMembers() is not None
                else None
            )
            if comparator_name is None:
                comparator = ASCENDING
            else:
                comparator = Comparator(comparator_name, first_members)
            levels[name] = Level(
                name,
                jlvl.getPropertyName(),
                _parse_detailed_type(jlvl.getType().getDetailType()),
                _comparator=comparator,
            )
        return levels

    def update_hierarchies_for_cube(
        self,
        cube: LocalCube[Any, Any, Any],
        *,
        structure: Mapping[str, Mapping[str, Mapping[str, str]]],
    ) -> None:
        java_structure = to_java_map(
            {
                dimension_name: to_java_map(
                    {
                        hierarchy_name: to_java_map(levels, gateway=self.gateway)
                        for hierarchy_name, levels in hierarchy.items()
                    },
                    gateway=self.gateway,
                )
                for dimension_name, hierarchy in structure.items()
            },
            gateway=self.gateway,
        )
        self.java_api.outsideTransactionApi().updateHierarchiesForCube(
            cube.name, java_structure
        )

    def create_analysis_hierarchy(
        self, name: str, *, cube: Cube, table_name: str, column_name: str
    ) -> None:
        """Create an analysis hierarchy from an existing table column."""
        self.java_api.outsideTransactionApi().createAnalysisHierarchy(
            cube.name,
            name,
            table_name,
            column_name,
        )

    def create_date_hierarchy(
        self,
        *,
        cube: Cube,
        table: Table,
        field: str,
        hierarchy_name: str,
        levels: Mapping[str, str],
    ) -> None:
        pair: Any = self.gateway.jvm.com.quartetfs.fwk.impl.Pair  # type: ignore
        converted = [pair(name, pattern) for (name, pattern) in levels.items()]
        levels_list = to_java_object_list(converted, gateway=self.gateway)
        self.java_api.outsideTransactionApi().createDateHierarchy(
            cube.name,
            table.name,
            field,
            hierarchy_name,
            levels_list,
        )

    def update_hierarchy_coordinate(
        self,
        *,
        cube: LocalCube[Any, Any, Any],
        hierarchy: Hierarchy,
        new_dim: str,
        new_hier: str,
    ) -> None:
        """Change the coordinate of a hierarchy."""
        self.java_api.outsideTransactionApi().updateHierarchyCoordinate(
            cube.name, hierarchy._java_description, f"{new_hier}@{new_dim}"
        )

    def update_hierarchy_slicing(self, hierarchy: Hierarchy, slicing: bool) -> None:
        """Update whether the hierarchy is slicing or not."""
        self.java_api.outsideTransactionApi().setHierarchySlicing(
            hierarchy._cube.name, hierarchy._java_description, slicing
        )

    def update_level_comparator(self, level: Level) -> None:
        """Change the level comparator."""
        comparator_name = (
            level.comparator._name if level.comparator is not None else None
        )
        first_members = None
        if level.comparator is not None and level.comparator._first_members is not None:
            first_members = to_java_object_array(
                level.comparator._first_members, gateway=self.gateway
            )

        if level._hierarchy is None:
            raise ValueError(f"Missing hierarchy for level {level.name}.")

        self.java_api.outsideTransactionApi().updateLevelComparator(
            level._hierarchy._cube.name,
            level._java_description,
            comparator_name,
            first_members,
        )

    def drop_level(self, level: Level) -> None:
        """Delete a level."""
        hierarchy = level._hierarchy
        if hierarchy is None:
            raise ValueError("No hierarchy for level " + level.name)
        self.java_api.outsideTransactionApi().deleteLevel(
            hierarchy._cube.name, level._java_description
        )

    def drop_hierarchy(
        self, cube: LocalCube[Any, Any, Any], hierarchy: Hierarchy
    ) -> None:
        """Drop a hierarchy from the cube."""
        self.java_api.outsideTransactionApi().dropHierarchy(
            cube.name, hierarchy._java_description
        )

    def retrieve_cubes(self) -> List[Any]:
        """Retrieve the cubes of the session."""
        return to_python_list(self.java_api.outsideTransactionApi().retrieveCubes())

    def retrieve_cube(self, cube_name: str) -> Any:
        """Retrieve a cube of the session using its name."""
        return self.java_api.outsideTransactionApi().retrieveCube(cube_name)

    def retrieve_hierarchies(
        self, cube: LocalCube[Any, Any, Any]
    ) -> Dict[Tuple[str, str], Hierarchy]:
        """Retrieve the hierarchies of the cube."""
        hierarchies: Dict[Tuple[str, str], Hierarchy] = {}
        java_hierarchies = self.java_api.outsideTransactionApi().retrieveHierarchies(
            cube.name
        )
        python_hierarchies = self._convert_to_python_hierarchies(
            cube, to_python_dict(java_hierarchies).values()
        )
        for hierarchy in python_hierarchies:
            hierarchies[(hierarchy.dimension, hierarchy.name)] = hierarchy
        return hierarchies

    def retrieve_hierarchy(
        self, name: str, *, cube: LocalCube[Any, Any, Any], dimension: Optional[str]
    ) -> List[Hierarchy]:
        """Retrieve a cube's hierarchy."""
        # Get the hierarchy from the java side.
        java_hierarchies = to_python_list(
            self.java_api.outsideTransactionApi().retrieveHierarchy(
                cube.name, dimension, name
            )
        )

        return self._convert_to_python_hierarchies(cube, java_hierarchies)

    def retrieve_hierarchy_for_level(
        self,
        level_name: str,
        *,
        cube: LocalCube[Any, Any, Any],
        dimension_name: Optional[str],
        hierarchy_name: Optional[str],
    ) -> List[Hierarchy]:
        """Retrieve the hierarchy containing a level with the given name."""
        java_hierarchies = to_python_list(
            self.java_api.outsideTransactionApi().retrieveHierarchyForLevel(
                cube.name, dimension_name, hierarchy_name, level_name
            )
        )
        return self._convert_to_python_hierarchies(cube, java_hierarchies)

    def _convert_to_python_hierarchies(
        self, cube: LocalCube[Any, Any, Any], java_hierarchies: Any
    ) -> List[Hierarchy]:
        """Convert java hierarchies to python ones."""
        hierarchies = []
        for java_hierarchy in java_hierarchies:
            hierarchy = Hierarchy(
                java_hierarchy.getName(),
                JavaApi._convert_from_java_levels(java_hierarchy.getLevels()),
                java_hierarchy.getDimensionName(),
                java_hierarchy.getSlicing(),
                cube,
                self,
                java_hierarchy.getVisible(),
            )
            for level in hierarchy.levels.values():
                level._hierarchy = hierarchy
            hierarchies.append(hierarchy)
        return hierarchies

    def set_hierarchy_visibility(
        self,
        *,
        cube: LocalCube[Any, Any, Any],
        dimension: Optional[str],
        name: str,
        visible: bool,
    ) -> None:
        self.java_api.outsideTransactionApi().setHierarchyVisibility(
            cube.name, dimension, name, visible
        )

    def set_measure_folder(
        self, *, cube_name: str, measure: MeasureDescription, folder: Optional[str]
    ) -> None:
        """Set the folder of a measure."""
        self.java_api.outsideTransactionApi().setMeasureFolder(
            cube_name, measure.name, folder
        )

    def set_measure_formatter(
        self, *, cube_name: str, measure: MeasureDescription, formatter: Optional[str]
    ) -> None:
        """Set the formatter of a measure."""
        self.java_api.outsideTransactionApi().setMeasureFormatter(
            cube_name, measure.name, formatter
        )

    def set_visible(
        self, *, cube_name: str, measure: MeasureDescription, visible: Optional[bool]
    ) -> None:
        """Set the visibility of a measure."""
        self.java_api.outsideTransactionApi().setMeasureVisibility(
            cube_name, measure.name, visible
        )

    def set_measure_description(
        self, *, cube_name: str, measure: Measure, description: Optional[str]
    ) -> None:
        """Set the measure description."""
        self.java_api.outsideTransactionApi().setMeasureDescription(
            cube_name, measure.name, description
        )

    @dataclass(frozen=True)
    class JavaMeasureDescription:
        """Description of a measure to build."""

        folder: str
        formatter: str
        visible: bool
        underlying_type: DataType
        description: Optional[str]

    def get_full_measures(
        self, cube: LocalCube[Any, Any, Any]
    ) -> Dict[str, JavaApi.JavaMeasureDescription]:
        """Retrieve the list of the cube's measures, including their required levels."""
        java_measures = self.java_api.outsideTransactionApi().getFullMeasures(cube.name)
        measures = to_python_list(java_measures)
        final_measures: Dict[str, JavaApi.JavaMeasureDescription] = {}
        for measure in measures:
            final_measures[measure.getName()] = JavaApi.JavaMeasureDescription(
                measure.getFolder(),
                measure.getFormatter(),
                measure.isVisible(),
                _parse_detailed_type(measure.getType()),
                measure.getDescription(),
            )
        return final_measures

    def get_measure(
        self, cube: LocalCube[Any, Any, Any], measure_name: str
    ) -> JavaApi.JavaMeasureDescription:
        """Retrieve all the details about a measure defined in the cube."""
        measure = self.java_api.outsideTransactionApi().getMeasure(
            cube.name, measure_name
        )
        return JavaApi.JavaMeasureDescription(
            measure.getFolder(),
            measure.getFormatter(),
            measure.isVisible(),
            _parse_detailed_type(measure.getType()),
            measure.getDescription(),
        )

    def get_required_levels(self, measure: Measure) -> List[str]:
        """Get the required levels of a measure."""
        return to_python_list(
            self.java_api.outsideTransactionApi().getRequiredLevels(
                measure._cube.name, measure.name
            )
        )

    @staticmethod
    def create_retrieval(jretr: Any) -> RetrievalData:
        """Convert Java retrieval to Python."""
        loc_str = ", ".join(
            [
                str(loc.getDimension())
                + "@"
                + str(loc.getHierarchy())
                + "@"
                + "\\".join(to_python_list(loc.getLevel()))
                + ": "
                + "\\".join(str(x) for x in to_python_list(loc.getPath()))
                for loc in to_python_list(jretr.getLocation())
            ]
        )
        timings = to_python_dict(jretr.getTimingInfo())
        return RetrievalData(
            id=jretr.getRetrievalId(),
            retrieval_type=jretr.getType(),
            location=loc_str,
            filter_id=jretr.getFilterId(),
            measures=to_python_list(jretr.getMeasures()),
            start_times=list(timings.get("startTime", [])),
            elapsed_times=list(timings.get("elapsedTime", [])),
            result_size=jretr.getResultSize(),
            retrieval_filter=str(jretr.getFilterId()),
            partitioning=jretr.getPartitioning(),
            measures_provider=jretr.getMeasureProvider(),
        )

    @staticmethod
    def create_query_plan(jplan: Any) -> QueryPlan:
        """Create a query plan."""
        jinfos = jplan.getPlanInfo()
        infos = {
            "ActivePivot": {
                "Type": jinfos.getPivotType(),
                "Id": jinfos.getPivotId(),
                "Branch": jinfos.getBranch(),
                "Epoch": jinfos.getEpoch(),
            },
            "Cube filters": {
                f.getId(): f.getDescription()
                for f in to_python_list(jplan.getQueryFilters())
            },
            "Continuous": jinfos.isContinuous(),
            "Range sharing": jinfos.getRangeSharing(),
            "Missed prefetches": jinfos.getMissedPrefetchBehavior(),
            "Cache": jinfos.getAggregatesCache(),
            "Global timings (ms)": to_python_dict(jinfos.getGlobalTimings()),
        }
        retrievals = [
            JavaApi.create_retrieval(plan)
            for plan in to_python_list(jplan.getAggregateRetrievals())
        ]
        dependencies = {
            key: to_python_list(item)
            for key, item in to_python_dict(jplan.getDependencies()).items()
        }
        return QueryPlan(infos=infos, retrievals=retrievals, dependencies=dependencies)

    def analyse_mdx(self, mdx: str, timeout: int) -> QueryAnalysis:
        """Analyse an MDX query on a given cube."""
        jplans = to_python_list(
            self.java_api.outsideTransactionApi().analyseMdx(mdx, timeout)
        )
        plans = [
            JavaApi.create_query_plan(jplan)
            for jplan in jplans
            if jplan.getPlanInfo().getClass().getSimpleName() == "PlanInfoData"
        ]
        return QueryAnalysis(plans)

    def copy_measure(
        self,
        copied_measure: MeasureDescription,
        new_name: str,
        *,
        cube_name: str,
    ) -> None:
        """Copy a measure."""
        self.java_api.outsideTransactionApi().copyMeasure(
            cube_name, copied_measure.name, new_name
        )

    def create_measure(  # pylint: disable=too-many-positional-parameters
        self,
        cube: Cube,
        measure_name: Optional[str],
        measure_plugin_key: str,
        *args: Any,
    ) -> str:
        """Create a new measure with by giving its constructor arguments."""
        return self.java_api.outsideTransactionApi().createMeasure(
            cube.name,
            measure_name,
            measure_plugin_key,
            to_java_object_array(
                [self.levels_to_descriptions(arg) for arg in args],
                gateway=self.gateway,
            ),
        )

    def register_aggregation_function(
        self,
        *,
        additional_imports: Iterable[str],
        additional_methods: Iterable[str],
        contribute_source_code: str,
        decontribute_source_code: Optional[str],
        merge_source_code: str,
        terminate_source_code: str,
        buffer_types: Iterable[DataType],
        output_type: DataType,
        plugin_key: str,
    ) -> None:
        """Register a new user defined aggregation function."""
        java_output_type = self._get_java_type(output_type)
        java_buffer_types = self._create_java_types_list(buffer_types)
        java_imports = ListConverter().convert(
            additional_imports, self.gateway._gateway_client
        )
        java_methods = ListConverter().convert(
            additional_methods, self.gateway._gateway_client
        )
        self.java_api.outsideTransactionApi().registerUserDefinedAggregateFunction(
            contribute_source_code,
            decontribute_source_code,
            merge_source_code,
            terminate_source_code,
            java_buffer_types,
            java_output_type,
            plugin_key,
            java_imports,
            java_methods,
        )

    def levels_to_descriptions(self, arg: Any) -> Any:
        """Recursively convert levels and hierarchies to their java descriptions."""
        if isinstance(arg, Level):
            return arg._java_description
        if isinstance(arg, Hierarchy):
            return arg._java_description
        if isinstance(arg, Tuple):
            return to_java_object_array(
                tuple(self.levels_to_descriptions(e) for e in arg),
                gateway=self.gateway,
            )
        if isinstance(arg, Mapping):
            return to_java_map(
                {
                    self.levels_to_descriptions(k): self.levels_to_descriptions(v)
                    for k, v in arg.items()
                },
                gateway=self.gateway,
            )
        if isinstance(arg, (List, Set)):
            return ListConverter().convert(
                [self.levels_to_descriptions(e) for e in arg],
                self.gateway._gateway_client,
            )
        return arg

    def aggregated_measure(
        self,
        *,
        cube: Cube,
        measure_name: Optional[str],
        table_name: str,
        column_name: str,
        agg_function: str,
        required_levels: Iterable[Level],
    ) -> str:
        """Create a new aggregated measure and return its name."""
        java_required_levels = to_java_string_array(
            convert_level_in_description(required_levels), gateway=self.gateway
        )
        return self.java_api.outsideTransactionApi().aggregatedMeasure(
            cube.name,
            measure_name,
            table_name,
            column_name,
            agg_function,
            java_required_levels,
        )

    def value_measure(
        self,
        *,
        cube: Cube,
        measure_name: Optional[str],
        table_name: str,
        column_name: str,
        column_type: DataType,
        required_levels: Optional[Iterable[Level]],
    ) -> str:
        """Create a new table value measure and return its name."""
        java_required_levels = (
            to_java_string_array(
                convert_level_in_description(required_levels), gateway=self.gateway
            )
            if required_levels is not None
            else None
        )
        # pylint: disable=invalid-name
        JavaColumnType: Any = self.gateway.jvm.io.atoti.loading.impl.TypeImpl  # type: ignore
        # pylint: enable=invalid-name
        java_type = JavaColumnType(column_type.java_type, column_type.nullable)
        return self.java_api.outsideTransactionApi().createValueMeasure(
            cube.name,
            measure_name,
            table_name,
            column_name,
            java_type,
            java_required_levels,
        )

    def delete_measure(self, *, cube: Cube, measure_name: str) -> bool:
        """Delete a measure and return ``True`` if the measure has been found and deleted."""
        return self.java_api.outsideTransactionApi().deleteMeasure(
            cube.name, measure_name
        )

    def create_parameter_simulation(
        self,
        *,
        cube: Cube,
        simulation_name: str,
        measures: Mapping[str, Optional[Union[float, int]]],
        levels: Iterable[Level],
        base_scenario_name: str,
    ) -> str:
        """Create a simulation in the cube and return the name of its backing table."""
        jmeasures = to_java_map(measures, gateway=self.gateway)
        jlevels = to_java_string_array(
            convert_level_in_description(levels), gateway=self.gateway
        )
        return self.java_api.outsideTransactionApi().createParameterSimulation(
            cube.name, simulation_name, jlevels, base_scenario_name, jmeasures
        )

    def block_until_widget_loaded(self, widget_id: str) -> bool:
        """Block until the widget is loaded or the JupyterLab extension is found unresponsive."""
        return self.java_api.blockUntilWidgetLoaded(widget_id)

    def get_shared_context_values(self, cube_name: str) -> Dict[str, str]:
        return to_python_dict(
            self.java_api.outsideTransactionApi().getCubeShareContextValues(cube_name)
        )

    def set_shared_context_value(self, *, cube_name: str, key: str, value: str) -> None:
        self.java_api.outsideTransactionApi().setCubeSharedContextValue(
            cube_name, key, value
        )

    def get_user(self, *args: Any, **kwargs: Any) -> Any:  # pylint: disable=no-self-use
        raise MissingPluginError("plus")

    def get_users(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def create_user(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def update_user_roles(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def change_user_password(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")

    def delete_user(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("plus")


def to_date(value: Any) -> Any:
    """Convert a Java date to a Python one."""
    try:
        if pd.isna(value):  # raises TypeError for JavaMember
            return None
    except TypeError:
        pass
    try:
        return pd.to_datetime(value.toString())
    except Exception:  # pylint: disable=broad-except
        return value
