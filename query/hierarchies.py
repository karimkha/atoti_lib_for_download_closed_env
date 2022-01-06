from typing import Tuple

from .._base._base_hierarchies import BaseHierarchies, _HierarchyKey
from .._mappings import ImmutableMapping
from .hierarchy import QueryHierarchy


class QueryHierarchies(
    ImmutableMapping[Tuple[str, str], QueryHierarchy], BaseHierarchies[QueryHierarchy]
):
    """Manage the query hierarchies."""

    def __getitem__(self, key: _HierarchyKey) -> QueryHierarchy:
        """Return the hierarchy with the given name."""
        if isinstance(key, tuple):
            return super().__getitem__(key)
        matching_hierarchies = [
            hierarchy for hierarchy in self.values() if hierarchy.name == key
        ]
        if len(matching_hierarchies) == 0:
            raise KeyError(f"Unknown hierarchy: {key}")
        if len(matching_hierarchies) == 1:
            return matching_hierarchies[0]
        raise self._multiple_hierarchies_error(key, matching_hierarchies)
