from __future__ import annotations

from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

import pandas as pd
import pyarrow as pa
from typing_extensions import Literal

from ._arrow import arrow_to_pandas, run_raw_arrow_query
from ._base._base_cube import BaseCube
from ._base._base_level import BaseLevel
from ._bitwise_operators_only import IdentityElement
from ._docs_utils import EXPLAIN_QUERY_DOC, QUERY_DOC, doc, get_query_args_doc
from ._hierarchy_isin_conditions import HierarchyIsInCondition
from ._java_api import JavaApi
from ._level_conditions import LevelCondition
from ._level_isin_conditions import LevelIsInCondition
from ._local_hierarchies import LocalHierarchies
from ._local_measures import LocalMeasures
from ._multi_condition import MultiCondition
from ._query_plan import QueryAnalysis
from ._scenario_utils import BASE_SCENARIO_NAME
from ._type_utils import typecheck
from .aggregates_cache import AggregatesCache
from .experimental._distributed.levels import DistributedLevels
from .levels import Levels
from .measure import Measure
from .query._cellset import LevelCoordinates
from .query.cube import _decombine_condition
from .query.level import QueryLevel
from .query.measure import QueryMeasure
from .query.query_result import QueryResult

if TYPE_CHECKING:
    from ._local_session import LocalSession

_Level = TypeVar("_Level", bound=BaseLevel)
_Levels = TypeVar("_Levels", Levels, DistributedLevels)
_Measure = Union[Measure, QueryMeasure]
_LocalMeasures = TypeVar("_LocalMeasures", bound="LocalMeasures")
_LocalHierarchies = TypeVar("_LocalHierarchies", bound="LocalHierarchies")


_QUERY_ARGS_WITH_MODE_DOC = f"""{get_query_args_doc(is_query_session=False)}
            mode: The query mode.

              * ``"pretty"`` is best for queries returning small results:

                * A :class:`~atoti.query.query_result.QueryResult` will be returned and its rows will be sorted according to the level comparators.

                Example:

                    .. doctest:: query

                        >>> cube.query(
                        ...     m["Price.SUM"],
                        ...     levels=[l["Continent"]],
                        ...     mode="pretty",
                        ... )
                                  Price.SUM
                        Continent
                        America      510.00
                        Europe       470.00

              *  ``"raw"`` is best for benchmarks or large exports:

                * A faster and more efficient endpoint reducing the data transfer from Java to Python will be used.
                * A classic :class:`pandas.DataFrame` will be returned.
                * ``include_totals="True"`` will not be allowed.
                * The :guilabel:`Convert to Widget Below` action provided by the :mod:`atoti-jupyterlab <atoti_jupyterlab>` plugin will not be available.

                Example:

                    .. doctest:: query

                        >>> cube.query(
                        ...     m["Price.SUM"],
                        ...     levels=[l["Continent"]],
                        ...     mode="raw",
                        ... )
                          Continent  Price.SUM
                        0    Europe      470.0
                        1   America      510.0
"""


@typecheck
class LocalCube(BaseCube[_LocalHierarchies, _Levels, _LocalMeasures]):
    """Local cube class."""

    def __init__(
        self,
        name: str,
        *,
        java_api: JavaApi,
        session: LocalSession[Any],
        hierarchies: _LocalHierarchies,
        level_function: Callable[[_LocalHierarchies], _Levels],
        measures: _LocalMeasures,
        agg_cache: AggregatesCache,
    ):
        """Init."""
        super().__init__(name, hierarchies, measures)
        self._session = session
        self._java_api = java_api
        self._levels = level_function(hierarchies)
        self._agg_cache = agg_cache

    @property
    def name(self) -> str:
        """Name of the cube."""
        return self._name

    @property
    def hierarchies(self) -> _LocalHierarchies:
        """Hierarchies of the cube."""
        return self._hierarchies

    @property
    def levels(self) -> _Levels:
        """Levels of the cube."""
        return self._levels

    @property
    def measures(self) -> _LocalMeasures:
        """Measures of the cube."""
        return self._measures

    @property
    def aggregates_cache(self) -> AggregatesCache:  # noqa: D401
        """Aggregates cache of the cube."""
        return self._agg_cache

    @abstractmethod
    def _get_level_data_types(
        self, levels_coordinates: Iterable[LevelCoordinates]
    ) -> Dict[LevelCoordinates, str]:
        ...

    @doc(QUERY_DOC, args=_QUERY_ARGS_WITH_MODE_DOC)
    def query(
        self,
        *measures: _Measure,
        condition: Optional[
            Union[
                LevelCondition,
                MultiCondition,
                LevelIsInCondition,
                HierarchyIsInCondition,
            ]
        ] = None,
        include_totals: bool = False,
        levels: Iterable[_Level] = (),
        mode: Literal["pretty", "raw"] = "pretty",
        scenario: str = BASE_SCENARIO_NAME,
        timeout: int = 30,
    ) -> Union[QueryResult, pd.DataFrame]:
        if mode == "pretty":
            mdx = self._generate_mdx(
                condition=condition,
                include_totals=include_totals,
                levels=levels,
                measures=measures,
                scenario_name=scenario,
            )
            query_result = self._session.query_mdx(
                mdx, keep_totals=include_totals, timeout=timeout
            )
            return query_result

        if include_totals:
            raise ValueError("""Totals cannot be included in "raw" mode.""")

        # Raw query
        # Note: Converting to pandas is fast for small tables (<100K) but can take several seconds for large datasets
        return arrow_to_pandas(
            self._query_as_arrow(
                condition=condition,
                levels=levels,
                measures=measures,
                scenario_name=scenario,
                timeout=timeout,
            )
        )

    def _query_as_arrow(
        self,
        *,
        condition: Optional[
            Union[
                LevelCondition,
                MultiCondition,
                LevelIsInCondition,
                HierarchyIsInCondition,
            ]
        ] = None,
        levels: Iterable[_Level],
        measures: Iterable[_Measure],
        scenario_name: str = BASE_SCENARIO_NAME,
        timeout: int = 30,
    ) -> pa.Table:
        params = {
            "cubeName": self.name,
            "branch": scenario_name,
            "measures": [m.name for m in measures],
            "levelCoordinates": [level._java_description for level in levels],
            **_serialize_conditions(condition),
            "timeout": timeout,
        }
        return run_raw_arrow_query(
            params,
            session=self._session._open_transient_query_session(),
        )

    @doc(EXPLAIN_QUERY_DOC, corresponding_method="query")
    def explain_query(
        self,
        *measures: _Measure,
        condition: Optional[
            Union[
                LevelCondition,
                MultiCondition,
                LevelIsInCondition,
                HierarchyIsInCondition,
            ]
        ] = None,
        include_totals: bool = False,
        levels: Iterable[_Level] = (),
        scenario: str = BASE_SCENARIO_NAME,
        timeout: int = 30,
    ) -> QueryAnalysis:
        mdx = self._generate_mdx(
            condition=condition,
            include_totals=include_totals,
            levels=levels,
            measures=measures,
            scenario_name=scenario,
        )
        return self._java_api.analyse_mdx(mdx, timeout)

    def _generate_mdx(
        self,
        *,
        condition: Optional[
            Union[
                LevelCondition,
                MultiCondition,
                LevelIsInCondition,
                HierarchyIsInCondition,
            ]
        ] = None,
        include_totals: bool,
        levels: Iterable[_Level],
        measures: Iterable[_Measure],
        scenario_name: str,
    ) -> str:
        query_measures = [
            QueryMeasure(
                measure.name,
                measure.visible,
                measure.folder,
                measure.formatter,
                measure.description,
            )
            for measure in measures
        ]
        query_levels = [
            QueryLevel(level.name, level.dimension, level.hierarchy) for level in levels
        ]
        return (
            self._session._open_transient_query_session()
            .cubes[self.name]
            ._generate_mdx(
                condition=condition,
                include_totals=include_totals,
                levels=query_levels,
                measures=query_measures,
                scenario_name=scenario_name,
            )
        )

    def _identity(self) -> Tuple[IdentityElement, ...]:
        return (
            self._name,
            self._session.name,
        )


def _serialize_conditions(
    condition: Optional[
        Union[
            LevelCondition,
            MultiCondition,
            LevelIsInCondition,
            HierarchyIsInCondition,
        ]
    ]
) -> Dict[str, Any]:
    (
        level_conditions,
        level_isin_condition,
        hierarchy_isin_condition,
    ) = _decombine_condition(condition)

    # Ensure there is no hierarchy conditions
    if hierarchy_isin_condition:
        raise ValueError("Unsupported hierarchy isin condition in raw query mode.")

    # Ensure all condition are == or isin on strings
    for level_condition in level_conditions:
        if level_condition._operation != "eq":
            raise ValueError(
                f"'{level_condition._operation}' not supported in query condition: level conditions can only be based on equality (==) or isin."
            )
        if not isinstance(level_condition._value, str):
            raise TypeError(
                f"Type {type(level_condition._value)} not supported in query condition: level conditions can only be based on equality with strings."
            )
    for isin_condition in level_isin_condition:
        not_string = [
            value for value in isin_condition._members if not isinstance(value, str)
        ]
        if not_string:
            raise TypeError(
                f"Only strings are supported in query condition but the following values are not strings: {str(not_string)}."
            )
    # Serialize the conditions
    equal_conditions = {
        level_condition._level._java_description: level_condition._value
        for level_condition in level_conditions
    }
    isin_conditions = {
        level_condition._level._java_description: level_condition._members
        for level_condition in level_isin_condition
    }
    return {
        "equalConditions": equal_conditions,
        "isinConditions": isin_conditions,
    }
