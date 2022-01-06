from typing import Optional

from ..._base._base_levels import BaseLevels
from ..._level_utils import raise_multiple_levels_error
from ...query.level import QueryLevel
from .hierarchies import DistributedHierarchies


class DistributedLevels(BaseLevels[QueryLevel, DistributedHierarchies]):
    """Flat representation of all the levels in the cube."""

    def _find_level(
        self,
        level_name: str,
        *,
        dimension_name: Optional[str] = None,
        hierarchy_name: Optional[str] = None,
    ) -> QueryLevel:
        if dimension_name is None:
            if hierarchy_name is None:
                level = self._flatten()[level_name]
                if level is not None:
                    return level

                return raise_multiple_levels_error(
                    level_name, list(self._hierarchies.values())
                )

            return self._hierarchies[hierarchy_name][level_name]
        return self._hierarchies[(dimension_name, hierarchy_name)][level_name]  # type: ignore
