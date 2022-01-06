from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Tuple, Union

from typeguard import typechecked, typeguard_ignore

from .._base._base_cube import BaseCube
from .._docs_utils import QUERY_DOC, doc, get_query_args_doc
from .._hierarchy_isin_conditions import HierarchyIsInCondition
from .._level_conditions import LevelCondition
from .._level_isin_conditions import LevelIsInCondition
from .._multi_condition import MultiCondition
from .._scenario_utils import BASE_SCENARIO_NAME
from ._mdx_utils import generate_mdx
from ._widget_conversion_details import WidgetConversionDetails
from .hierarchies import QueryHierarchies
from .level import QueryLevel
from .levels import QueryLevels
from .measure import QueryMeasure
from .measures import QueryMeasures
from .query_result import QueryResult

if TYPE_CHECKING:
    from .session import QuerySession


@typeguard_ignore
@dataclass(frozen=True)
class QueryCube(BaseCube[QueryHierarchies, QueryLevels, QueryMeasures]):
    """Query cube."""

    _session: QuerySession = field(repr=False)

    @property
    def levels(self) -> QueryLevels:
        """Levels of the cube."""
        return QueryLevels(self.hierarchies)

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
        levels: Iterable[QueryLevel],
        measures: Iterable[QueryMeasure],
        scenario_name: str,
    ) -> str:
        (
            level_conditions,
            level_isin_conditions,
            hierarchy_isin_conditions,
        ) = _decombine_condition(condition)

        return generate_mdx(
            cube=self,
            hierarchy_isin_conditions=hierarchy_isin_conditions,
            include_totals=include_totals,
            level_conditions=level_conditions,
            level_isin_conditions=level_isin_conditions,
            levels=levels,
            measures=measures,
            scenario_name=scenario_name,
        )

    @doc(QUERY_DOC, args=get_query_args_doc(is_query_session=True))
    @typechecked
    def query(
        self,
        *measures: QueryMeasure,
        condition: Optional[
            Union[
                LevelCondition,
                MultiCondition,
                LevelIsInCondition,
                HierarchyIsInCondition,
            ]
        ] = None,
        include_totals: bool = False,
        levels: Iterable[QueryLevel] = (),
        scenario: str = BASE_SCENARIO_NAME,
        timeout: int = 30,
        **kwargs: Any,
    ) -> QueryResult:
        if levels is None:
            levels = []

        mdx = self._generate_mdx(
            condition=condition,
            include_totals=include_totals,
            levels=levels,
            measures=measures,
            scenario_name=scenario,
        )

        query_result = self._session.query_mdx(
            mdx, keep_totals=include_totals, timeout=timeout, **kwargs
        )

        # Remove this branch when https://github.com/activeviam/atoti/issues/1943 is done.
        if not measures:
            query_result._atoti_widget_conversion_details = None

        # Always use an MDX including totals because ActiveUI 5 then relies on context values to show/hide totals.
        if not include_totals and query_result._atoti_widget_conversion_details:
            query_result._atoti_widget_conversion_details = WidgetConversionDetails(
                mdx=self._generate_mdx(
                    condition=condition,
                    include_totals=True,
                    levels=levels,
                    measures=measures,
                    scenario_name=scenario,
                ),
                session_id=query_result._atoti_widget_conversion_details.session_id,
                widget_creation_code=query_result._atoti_widget_conversion_details.widget_creation_code,
            )

        return query_result


def _decombine_condition(
    condition: Optional[
        Union[
            LevelCondition,
            MultiCondition,
            LevelIsInCondition,
            HierarchyIsInCondition,
        ]
    ] = None,
) -> Tuple[
    List[LevelCondition],
    List[LevelIsInCondition],
    List[HierarchyIsInCondition],
]:
    level_conditions: List[LevelCondition] = []
    level_isin_conditions: List[LevelIsInCondition] = []
    hierarchy_isin_conditions: List[HierarchyIsInCondition] = []

    if condition is not None:
        if isinstance(condition, LevelCondition):
            level_conditions.append(condition)
        elif isinstance(condition, LevelIsInCondition):
            level_isin_conditions.append(condition)
        elif isinstance(condition, HierarchyIsInCondition):
            hierarchy_isin_conditions.append(condition)
        else:
            measure_conditions = condition._measure_conditions
            if measure_conditions:
                raise ValueError(
                    f"Multi-conditions with measures are not supported when querying cube:"
                    f" {measure_conditions}"
                )
            level_conditions += condition._level_conditions
            level_isin_conditions += condition._level_isin_conditions
            hierarchy_isin_conditions += condition._hierarchy_isin_condition

    return level_conditions, level_isin_conditions, hierarchy_isin_conditions
