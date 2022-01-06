from typing import Optional

from ._base._base_levels import BaseLevels, _LevelKey
from ._level_utils import raise_multiple_levels_error
from .hierarchies import Hierarchies
from .level import Level


class Levels(BaseLevels[Level, Hierarchies]):
    """Flat representation of all the levels in the cube."""

    def __delitem__(self, key: _LevelKey) -> None:
        """Delete a level.

        Args:
            key: The name of the level to delete, or a ``(hierarchy_name, level_name)`` tuple.
        """
        if key not in self:
            raise KeyError(f"{key} is not an existing level.")
        level = self[key]
        hierarchy = level._hierarchy
        if hierarchy is None:
            raise ValueError("No hierarchy defined for level " + level.name)
        hierarchy._java_api.drop_level(level)
        hierarchy._java_api.refresh()

    def _find_level(
        self,
        level_name: str,
        *,
        dimension_name: Optional[str] = None,
        hierarchy_name: Optional[str] = None,
    ) -> Level:
        """Get a level from the hierarchy name and level name."""
        hierarchies = self._hierarchies._java_api.retrieve_hierarchy_for_level(
            level_name,
            cube=self._hierarchies._cube,
            dimension_name=dimension_name,
            hierarchy_name=hierarchy_name,
        )
        if len(hierarchies) > 1:
            raise_multiple_levels_error(level_name, hierarchies)

        if len(hierarchies) == 0:
            raise KeyError(f"No level with name {level_name} found in cube.")

        hierarchy = hierarchies[0]

        return hierarchy.levels[level_name]
