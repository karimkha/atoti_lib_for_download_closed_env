from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Collection,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Union,
)
from warnings import warn

import pandas as pd
from typeguard import typechecked, typeguard_ignore

from ._functions.measure import value
from ._ipython_utils import running_in_ipython
from ._local_cube import LocalCube
from ._providers import PartialAggregateProvider
from ._repr_utils import ReprJson, ReprJsonable
from ._scenario_utils import BASE_SCENARIO_NAME
from .aggregates_cache import AggregatesCache
from .exceptions import AtotiJavaException
from .hierarchies import Hierarchies
from .level import Level
from .levels import Levels
from .measures import Measures
from .query._cellset import LevelCoordinates
from .table import Column, Table
from .tables import _GRAPHVIZ_MESSAGE
from .type import INT, DataType

if TYPE_CHECKING:
    from ._java_api import JavaApi
    from .session import Session


@dataclass(frozen=True)
class _ParameterSimulationPrivateParameters:
    measure_name: str
    default_value: Optional[Union[float, int]] = None


class Cube(LocalCube[Hierarchies, Levels, Measures]):
    """Cube of a :class:`~atoti.session.Session`."""

    @typeguard_ignore
    def __init__(
        self, name: str, *, java_api: JavaApi, base_table: Table, session: Session
    ):
        """Init."""
        super().__init__(
            name,
            java_api=java_api,
            session=session,
            hierarchies=Hierarchies(java_api, self),
            level_function=lambda hierarchies: Levels(hierarchies),
            measures=Measures(java_api, self),
            agg_cache=AggregatesCache(java_api, self),
        )
        self._base_table = base_table
        self._shared_context = CubeContext(java_api, self)

    @property
    def schema(self) -> Any:
        """Schema of the cube's tables as an SVG graph.

        Note:
            Graphviz is required to display the graph.
            It can be installed with Conda: ``conda install graphviz`` or by following the `download instructions <https://www.graphviz.org/download/>`__.

        Returns:
            An SVG image in IPython and a Path to the SVG file otherwise.
        """
        try:
            path = self._java_api.generate_cube_schema_image(self.name)
            if running_in_ipython():
                from IPython.display import SVG

                return SVG(filename=path)
            return Path(path)
        except AtotiJavaException:
            logging.getLogger("atoti.cube").warning(_GRAPHVIZ_MESSAGE)

    @property
    def shared_context(self) -> CubeContext:
        """Context values shared by all the users.

        Context values can also be set at query time, and per user, directly from the UI.
        The values in the shared context are the default ones for all the users.

        - ``queriesTimeLimit``

            The number of seconds after which a running query is cancelled and its resources reclaimed.
            Set to ``-1`` to remove the limit.
            Defaults to 30s.

        - ``queriesResultLimit.intermediateSize``

            The limit number of point locations for a single intermediate result.
            This works as a safe-guard to prevent queries from consuming too much memory, which is especially useful when going to production with several simulatenous users on the same server.
            Set to ``-1`` to use the maximum limit.
            In atoti, the maximum limit is the default while in Atoti+ it defaults to ``1000000``.

        - ``queriesResultLimit.tansientResultSize``

            Similar to *intermediateSize* but across all the intermediate results of the same query.
            Set to ``-1`` to use the maximum limit.
            In atoti, the maximum limit is the default while in Atoti+ it defaults to ``10000000``.

        Example:
            >>> df = pd.DataFrame(
            ...     columns=["City", "Price"],
            ...     data=[
            ...         ("London", 240.0),
            ...         ("New York", 270.0),
            ...         ("Paris", 200.0),
            ...     ],
            ... )
            >>> table = session.read_pandas(
            ...     df, keys=["City"], table_name="shared_context example"
            ... )
            >>> cube = session.create_cube(table)
            >>> cube.shared_context["queriesTimeLimit"] = 60
            >>> cube.shared_context["queriesResultLimit.intermediateSize"] = 1000000
            >>> cube.shared_context["queriesResultLimit.transientSize"] = 10000000
            >>> cube.shared_context
            {'queriesTimeLimit': '60', 'queriesResultLimit.intermediateSize': '1000000', 'queriesResultLimit.transientSize': '10000000'}

        """
        return self._shared_context

    @property
    def _aggregate_providers(self) -> Sequence[PartialAggregateProvider]:
        """Get the partial aggregate providers."""
        return self._java_api.get_aggregate_providers(self)

    @_aggregate_providers.setter
    def _aggregate_providers(self, providers: Sequence[PartialAggregateProvider]):
        """Set the partial aggregate providers."""
        self._java_api.set_aggregate_providers(self, providers)
        self._java_api.refresh()

    def _join_distributed_cluster(
        self, distributed_session_url: str, distributed_cube_name: str
    ):
        """Join the distributed cluster at the given address for the given distributed cube."""

        self._java_api.join_distributed_cluster(
            cube=self,
            distributed_session_url=distributed_session_url,
            distributed_cube_name=distributed_cube_name,
        )
        self._java_api.refresh()

    def _get_level_data_types(
        self, levels_coordinates: Iterable[LevelCoordinates]
    ) -> Dict[LevelCoordinates, str]:
        return {
            level_coordinates: (
                "object"
                if level_coordinates == ("Epoch", "Epoch", "Branch")
                else self.levels[level_coordinates].data_type.java_type
            )
            for level_coordinates in levels_coordinates
        }

    def _get_level_from_identifier(self, identifier: str) -> Level:
        """Get a level from its identifier."""
        [level, hierarchy, dimension] = identifier.split("@")
        return self.levels[(dimension, hierarchy, level)]

    def create_parameter_simulation(
        self,
        name: str,
        *,
        measures: Optional[Mapping[str, Optional[Union[float, int]]]] = None,
        levels: Iterable[Level] = (),
        base_scenario_name: str = BASE_SCENARIO_NAME,
        **kwargs: Any,
    ) -> Table:
        """Create a parameter simulation and its associated measures.

        Args:
            name: The name of the simulation.
              This is also the name of the corresponding table that will be created.
            measures: The mapping from the names of the created measures to their default value.
            levels: The levels to simulate on.
            base_scenario_name: The name of the base scenario.

        Example:

            >>> sales_table = session.read_csv(
            ...     f"{TUTORIAL_RESOURCES}/sales.csv",
            ...     table_name="Sales",
            ...     keys=["Sale ID"],
            ... )
            >>> shops_table = session.read_csv(
            ...     f"{TUTORIAL_RESOURCES}/shops.csv",
            ...     table_name="Shops",
            ...     keys=["Shop ID"],
            ... )
            >>> sales_table.join(shops_table, mapping={"Shop": "Shop ID"})
            >>> cube = session.create_cube(sales_table)
            >>> l, m = cube.levels, cube.measures

            Creating a parameter simulation on one level:

            >>> country_simulation = cube.create_parameter_simulation(
            ...     "Country simulation",
            ...     measures={"Country parameter": 1.0},
            ...     levels=[l["Country"]],
            ... )
            >>> country_simulation += ("France crash", "France", 0.8)
            >>> country_simulation.head()
                                  Country parameter
            Country Scenario
            France  France crash                0.8

            * ``France crash`` is the name of the scenario.
            * ``France`` is the coordinate at which the value will be changed.
            * ``0.8`` is the value the :guilabel:`Country parameter` measure will have in this scenario.

            >>> m["Unparametrized turnover"] = tt.agg.sum(
            ...     sales_table["Unit price"] * sales_table["Quantity"]
            ... )
            >>> m["Turnover"] = tt.agg.sum(
            ...     m["Unparametrized turnover"] * m["Country parameter"],
            ...     scope=tt.scope.origin(l["Country"]),
            ... )
            >>> cube.query(m["Turnover"], levels=[l["Country simulation"]])
                                  Turnover
            Country simulation
            Base                961,463.00
            France crash        889,854.60

            Drilldown to the :guilabel:`Country` level for more details:

            >>> cube.query(
            ...     m["Unparametrized turnover"],
            ...     m["Country parameter"],
            ...     m["Turnover"],
            ...     levels=[l["Country simulation"], l["Country"]],
            ... )
                                       Unparametrized turnover Country parameter    Turnover
            Country simulation Country
            Base               France               358,042.00              1.00  358,042.00
                               USA                  603,421.00              1.00  603,421.00
            France crash       France               358,042.00               .80  286,433.60
                               USA                  603,421.00              1.00  603,421.00

            Creating a parameter simulation on multiple levels:

            >>> size_simulation = cube.create_parameter_simulation(
            ...     "Size simulation",
            ...     measures={"Size parameter": 1.0},
            ...     levels=[l["Country"], l["Shop size"]],
            ... )
            >>> size_simulation += (
            ...     "Going local",
            ...     None,  # ``None`` serves as a wildcard matching any member value.
            ...     "big",
            ...     0.8,
            ... )
            >>> size_simulation += ("Going local", "USA", "small", 1.2)
            >>> m["Turnover"] = tt.agg.sum(
            ...     m["Unparametrized turnover"]
            ...     * m["Country parameter"]
            ...     * m["Size parameter"],
            ...     scope=tt.scope.origin(l["Country"], l["Shop size"]),
            ... )
            >>> cube.query(
            ...     m["Turnover"],
            ...     levels=[l["Size simulation"], l["Shop size"]],
            ... )
                                         Turnover
            Size simulation Shop size
            Base            big        120,202.00
                            medium     356,779.00
                            small      484,482.00
            Going local     big         96,161.60
                            medium     356,779.00
                            small      547,725.20

            When several rules contain ``None``, the one where the first ``None`` appears last takes precedence.

            >>> size_simulation += ("Going France and Local", "France", None, 2)
            >>> size_simulation += ("Going France and Local", None, "small", 10)
            >>> cube.query(
            ...     m["Unparametrized turnover"],
            ...     m["Turnover"],
            ...     levels=[l["Country"], l["Shop size"]],
            ...     condition=l["Size simulation"] == "Going France and Local",
            ... )
                              Unparametrized turnover      Turnover
            Country Shop size
            France  big                     47,362.00     94,724.00
                    medium                 142,414.00    284,828.00
                    small                  168,266.00    336,532.00
            USA     big                     72,840.00     72,840.00
                    medium                 214,365.00    214,365.00
                    small                  316,216.00  3,162,160.00

            Creating a parameter simulation without levels:

            >>> crisis_simulation = cube.create_parameter_simulation(
            ...     "Global Simulation",
            ...     measures={"Global parameter": 1.0},
            ... )
            >>> crisis_simulation += ("Global Crisis", 0.9)
            >>> m["Turnover"] = m["Unparametrized turnover"] * m["Global parameter"]
            >>> cube.query(m["Turnover"], levels=[l["Global Simulation"]])
                                 Turnover
            Global Simulation
            Base               961,463.00
            Global Crisis      865,316.70

            Creating a parameter simulation with multiple measures:

            >>> multi_parameter_simulation = cube.create_parameter_simulation(
            ...     "Price And Quantity",
            ...     measures={
            ...         "Price parameter": 1.0,
            ...         "Quantity parameter": 1.0,
            ...     },
            ... )
            >>> multi_parameter_simulation += ("Price Up Quantity Down", 1.2, 0.8)
            >>> m["Simulated Price"] = (
            ...     tt.value(sales_table["Unit price"]) * m["Price parameter"]
            ... )
            >>> m["Simulated Quantity"] = (
            ...     tt.value(sales_table["Quantity"]) * m["Quantity parameter"]
            ... )
            >>> m["Turnover"] = tt.agg.sum_product(
            ...     m["Simulated Price"],
            ...     m["Simulated Quantity"],
            ...     scope=tt.scope.origin(l["Sale ID"]),
            ... )
            >>> cube.query(m["Turnover"], levels=[l["Price And Quantity"]])
                                      Turnover
            Price And Quantity
            Base                    961,463.00
            Price Up Quantity Down  923,004.48



        """
        if kwargs:
            if measures is not None:
                raise ValueError(
                    "Cannot use the measures parameter and the deprecated measure_name or default_value parameter."
                )
            warn(
                "The measure_name and default_value parameters are deprecated, use the measures parameter instead.",
                category=FutureWarning,
                stacklevel=2,
            )
            private_parameters = _ParameterSimulationPrivateParameters(**kwargs)
            measures = {
                private_parameters.measure_name: private_parameters.default_value
            }
        if measures is None:
            raise ValueError(
                "At least one measure and its default value must be passed."
            )

        if any(level.name == "Scenario" for level in levels):
            raise ValueError(
                'Levels with the name "Scenario" cannot be used in parameter simulations.'
            )

        self._java_api.create_parameter_simulation(
            cube=self,
            simulation_name=name,
            levels=levels,
            base_scenario_name=base_scenario_name,
            measures=measures,
        )
        self._java_api.refresh()
        return Table(name, self._java_api)

    def create_parameter_hierarchy_from_column(self, name: str, column: Column) -> None:
        """Create a single-level hierarchy which dynamically takes its members from a column.

        Args:
            name: Name given to the created dimension, hierarchy and its single level.
            column: Column from which to take members.

        Example:
            >>> df = pd.DataFrame(
            ...     {
            ...         "Seller": ["Seller_1", "Seller_1", "Seller_2", "Seller_2"],
            ...         "ProductId": ["aBk3", "ceJ4", "aBk3", "ceJ4"],
            ...         "Price": [2.5, 49.99, 3.0, 54.99],
            ...     }
            ... )
            >>> table = session.read_pandas(df, table_name="Seller")
            >>> cube = session.create_cube(table)
            >>> l, m = cube.levels, cube.measures
            >>> cube.create_parameter_hierarchy_from_column(
            ...     "Competitor", table["Seller"]
            ... )
            >>> m["Price"] = tt.value(table["Price"])
            >>> m["Competitor price"] = tt.at(
            ...     m["Price"], coordinates={l["Seller"]: l["Competitor"]}
            ... )
            >>> cube.query(
            ...     m["Competitor price"],
            ...     levels=[l["Seller"], l["ProductId"]],
            ... )
                               Competitor price
            Seller   ProductId
            Seller_1 aBk3                  2.50
                     ceJ4                 49.99
            Seller_2 aBk3                  2.50
                     ceJ4                 49.99
            >>> cube.query(
            ...     m["Competitor price"],
            ...     levels=[l["Seller"], l["ProductId"]],
            ...     condition=l["Competitor"] == "Seller_2",
            ... )
                               Competitor price
            Seller   ProductId
            Seller_1 aBk3                  3.00
                     ceJ4                 54.99
            Seller_2 aBk3                  3.00
                     ceJ4                 54.99
        """
        self._java_api.create_analysis_hierarchy(
            name,
            cube=self,
            table_name=column._table.name,
            column_name=column.name,
        )
        self._java_api.refresh()

    def create_parameter_hierarchy_from_members(
        self,
        name: str,
        members: Collection[Any],
        *,
        data_type: Optional[DataType] = None,
        index_measure_name: Optional[str] = None,
    ) -> None:
        """Create a single-level hierarchy with the given members.

        It can be used as a parameter hierarchy in advanced analyses.

        Args:
            name: The name of hierarchy and its single level.
            members: The members of the hierarchy.
            data_type: The type with which the members will be stored.
                Automatically inferred by default.
            index_measure_name: The name of the indexing measure to create for this hierarchy, if any.

        Example:
            >>> df = pd.DataFrame(
            ...     {
            ...         "Seller": ["Seller_1", "Seller_2", "Seller_3"],
            ...         "Prices": [
            ...             [2.5, 49.99, 3.0, 54.99],
            ...             [2.6, 50.99, 2.8, 57.99],
            ...             [2.99, 44.99, 3.6, 59.99],
            ...         ],
            ...     }
            ... )
            >>> table = session.read_pandas(df, table_name="Seller prices")
            >>> cube = session.create_cube(table)
            >>> l, m = cube.levels, cube.measures
            >>> cube.create_parameter_hierarchy_from_members(
            ...     "ProductID",
            ...     ["aBk3", "ceJ4", "aBk5", "ceJ9"],
            ...     index_measure_name="Product index",
            ... )
            >>> m["Prices"] = tt.value(table["Prices"])
            >>> m["Product price"] = m["Prices"][m["Product index"]]
            >>> cube.query(
            ...     m["Product price"],
            ...     levels=[l["Seller"], l["ProductID"]],
            ... )
                               Product price
            Seller   ProductID
            Seller_1 aBk3               2.50
                     aBk5               3.00
                     ceJ4              49.99
                     ceJ9              54.99
            Seller_2 aBk3               2.60
                     aBk5               2.80
                     ceJ4              50.99
                     ceJ9              57.99
            Seller_3 aBk3               2.99
                     aBk5               3.60
                     ceJ4              44.99
                     ceJ9              59.99

        """
        index_column = f"{name} index"

        indices = list(range(len(members)))
        parameter_df = pd.DataFrame({name: members, index_column: indices})

        types = {index_column: INT}
        if data_type:
            types[name] = data_type
        elif all(
            isinstance(member, int) and -(2 ** 31) <= member < 2 ** 31
            for member in members
        ):
            types[name] = INT

        parameter_table = self._session.read_pandas(  # type: ignore
            parameter_df,
            table_name=name,
            keys=[name],
            types=types,
            hierarchized_columns=[name],  # index must not be hierarchized
            is_parameter_table=True,
        )

        self._base_table.join(parameter_table, mapping={})

        if index_measure_name:
            self.measures[index_measure_name] = value(parameter_table[index_column])

        self.hierarchies[name, name].slicing = True

        self._java_api.refresh()


@typeguard_ignore
@dataclass(frozen=True)
class CubeContext(MutableMapping[str, str], ReprJsonable):

    _java_api: JavaApi = field(repr=False)
    _cube: Cube = field(repr=False)

    def _get_values(self) -> Dict[str, str]:
        return self._java_api.get_shared_context_values(self._cube.name)

    @typechecked
    def __getitem__(self, key: str) -> str:
        return self._get_values()[key]

    @typechecked
    def __setitem__(  # pylint: disable=redefined-outer-name
        self, key: str, value: Any
    ) -> None:
        self._java_api.set_shared_context_value(
            cube_name=self._cube.name, key=key, value=str(value)
        )
        self._java_api.refresh()

    @typechecked
    def __delitem__(self, key: str) -> None:
        raise ValueError("Cannot delete context value.")

    def __iter__(self) -> Iterator:
        return iter(self._get_values())

    def __len__(self) -> int:
        return len(self._get_values())

    def _ipython_key_completions_(self) -> Sequence[str]:
        return list(self._get_values().keys())

    def __str__(self) -> str:
        return str(self._get_values())

    def __repr__(self) -> str:
        return repr(self._get_values())

    def _repr_json_(self) -> ReprJson:
        return (
            self._get_values(),
            {"expanded": True, "root": "Shared Context Values"},
        )
