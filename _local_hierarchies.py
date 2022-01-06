from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Mapping, Tuple, TypeVar, Union

from ._base._base_hierarchies import BaseHierarchies, _HierarchyKey
from ._base._base_hierarchy import BaseHierarchy
from ._mappings import DelegateMutableMapping
from .level import Level

if TYPE_CHECKING:
    from ._java_api import JavaApi
    from .cube import LocalCube
    from .hierarchy import Hierarchy
    from .table import Column

    LevelOrColumn = Union[Level, Column]

_BaseHierarchy = TypeVar("_BaseHierarchy", bound="BaseHierarchy")


@dataclass(frozen=True)
class LocalHierarchies(
    DelegateMutableMapping[Tuple[str, str], _BaseHierarchy],
    BaseHierarchies[_BaseHierarchy],
):
    """Local hierarchies class."""

    _java_api: JavaApi = field(repr=False)

    @abstractmethod
    def _get_underlying(self) -> Dict[Tuple[str, str], _BaseHierarchy]:
        """Fetch the hierarchies from the JVM each time they are needed."""

    def _update(self, mapping: Mapping[Tuple[str, str], _BaseHierarchy]) -> None:
        raise AttributeError(f"{self._get_name()} cube hierarchies cannot be changed.")

    def __delitem__(self, key: _HierarchyKey) -> None:
        """Delete the hierarchy.

        Args:
            key: The name of the hierarchy to delete.
        """
        raise AttributeError(f"{self._get_name()} cube hierarchies cannot be changed")

    def _get_name(self) -> str:
        return self.__class__.__name__.replace("Hierarchies", "")

    @staticmethod
    def _retrieve_hierarchies(
        java_api: JavaApi, cube: LocalCube[Any, Any, Any]
    ) -> Dict[Tuple[str, str], Hierarchy]:
        """Retrieve the hierarchies from the cube."""
        return java_api.retrieve_hierarchies(cube)
