from dataclasses import dataclass

from .._base._base_hierarchy import BaseHierarchy
from .._mappings import ImmutableMapping
from .level import QueryLevel


@dataclass(eq=False)
class QueryHierarchy(BaseHierarchy[ImmutableMapping[str, QueryLevel]]):
    """Hierarchy of a query cube."""

    _name: str
    _dimension: str
    _levels: ImmutableMapping[str, QueryLevel]
    _slicing: bool

    @property
    def levels(self) -> ImmutableMapping[str, QueryLevel]:
        return self._levels

    @property
    def dimension(self) -> str:
        return self._dimension

    @property
    def slicing(self) -> bool:
        return self._slicing

    @property
    def name(self) -> str:
        return self._name

    def __getitem__(self, key: str) -> QueryLevel:
        """Return the level with the given name.

        Args:
            key: The name of the requested level.
        """
        return self.levels[key]
