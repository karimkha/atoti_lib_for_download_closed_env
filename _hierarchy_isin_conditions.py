from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Collection, Mapping, Optional, Tuple

from ._condition import Condition
from .measure_description import MeasureConvertible

if TYPE_CHECKING:
    from ._base._base_hierarchy import BaseHierarchy
    from ._measures.boolean_measure import BooleanMeasure
    from ._multi_condition import MultiCondition


@dataclass(frozen=True)
class HierarchyIsInCondition(Condition, MeasureConvertible):
    """Class for isin condition on cube hierarchies."""

    _hierarchy: BaseHierarchy[Any]
    # Keys of subdict are level descriptions
    _members: Collection[Mapping[str, Any]]
    _operation: str = "hi"

    def __and__(self, other: Condition) -> MultiCondition:
        """Override the ``&`` bitwise operator to allow users to combine conditions."""
        from ._level_conditions import LevelCondition
        from ._level_isin_conditions import LevelIsInCondition
        from ._measures.boolean_measure import BooleanMeasure
        from ._multi_condition import MultiCondition

        if isinstance(other, BooleanMeasure):
            return MultiCondition(
                _hierarchy_isin_condition=(self,), _measure_conditions=(other,)
            )

        if isinstance(other, LevelCondition):
            return MultiCondition(
                _hierarchy_isin_condition=(self,), _level_conditions=(other,)
            )

        if isinstance(other, LevelIsInCondition):
            return MultiCondition(
                _hierarchy_isin_condition=(self,), _level_isin_conditions=(other,)
            )

        if isinstance(other, HierarchyIsInCondition):
            return MultiCondition(_hierarchy_isin_condition=(self, other))

        if isinstance(other, MultiCondition):
            return MultiCondition(
                other._level_conditions,
                other._measure_conditions,
                other._level_isin_conditions,
                tuple(other._hierarchy_isin_condition) + (self,),
            )

        raise ValueError("Invalid condition provided.")

    def _to_measure_description(
        self,
        agg_fun: Optional[str] = None,  # pylint: disable=unused-argument
    ) -> BooleanMeasure:
        """Convert this object into a measure.

        Args:
            agg_fun: The aggregation function.

        """
        from ._measures.boolean_measure import BooleanMeasure
        from .query.hierarchy import QueryHierarchy

        if isinstance(self._hierarchy, QueryHierarchy):
            raise ValueError(
                "Query hierarchy conditions cannot be converted to measures"
            )

        operands = []
        levels = list(self._hierarchy.levels.values())
        for sub_dict in self._members:
            condition = None
            for i, value in enumerate(sub_dict.values()):
                if condition is not None:
                    condition = condition & (levels[i] == value)
                else:
                    condition = levels[i] == value
            if condition is not None:
                operands.append(condition._to_measure_description())
        if len(operands) == 1:
            return operands[0]

        return BooleanMeasure("or", operands)


def create_condition_from_member_paths(
    hierarchy: BaseHierarchy[Any], *member_paths: Tuple[Any, ...]
) -> HierarchyIsInCondition:
    """Create condition from member paths."""
    members_list = []
    levels_coordinates = [
        level._java_description for level in hierarchy.levels.values()
    ]
    # build a dict [{"level_coord": value, "level_coord2": value2}, ...]
    for member_path in member_paths:
        temp = {}
        try:
            for i, member in enumerate(member_path):
                if member is None:
                    raise ValueError("None is not supported in isin conditions.")
                temp[levels_coordinates[i]] = member
        except IndexError:
            raise ValueError(
                f"Member paths cannot contain more than {len(hierarchy.levels)} elements which "
                f"is the number of levels of the {hierarchy.name} hierarchy."
            ) from None
        members_list.append(temp)

    return HierarchyIsInCondition(hierarchy, members_list)
