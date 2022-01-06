from __future__ import annotations

from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from .._repr_utils import ReprJson, ReprJsonable
from ..level import Level
from ._base_hierarchy import BaseHierarchy

if TYPE_CHECKING:
    from ..table import Column

    LevelOrColumn = Union[Level, Column]

_HierarchyKey = Union[str, Tuple[str, str]]
_BaseHierarchy = TypeVar("_BaseHierarchy", bound="BaseHierarchy")


class BaseHierarchies(Mapping[Tuple[str, str], _BaseHierarchy], ReprJsonable):
    """Manage the base hierarchies."""

    @abstractmethod
    def __getitem__(self, key: _HierarchyKey) -> _BaseHierarchy:
        """Return the hierarchy with the given name."""

    def _repr_json_(self) -> ReprJson:
        """Return the JSON representation of hierarchies."""
        dimensions: Dict[str, List[_BaseHierarchy]] = {}
        for hierarchy in self.values():
            dimensions.setdefault(hierarchy.dimension, []).append(hierarchy)
        json = {
            dimension: dict(
                sorted(
                    {
                        hierarchy._repr_json_()[1]["root"]: hierarchy._repr_json_()[0]
                        for hierarchy in dimension_hierarchies
                    }.items()
                )
            )
            for dimension, dimension_hierarchies in sorted(dimensions.items())
        }
        return json, {"expanded": True, "root": "Dimensions"}

    @staticmethod
    def _convert_key(key: _HierarchyKey) -> Tuple[Optional[str], str]:
        """Get the dimension and hierarchy from the key."""
        if isinstance(key, str):
            return (None, key)

        return key

    @staticmethod
    def _multiple_hierarchies_error(
        key: _HierarchyKey, hierarchies: Iterable[_BaseHierarchy]
    ) -> KeyError:
        """Get the error to raise when multiple hierarchies match the key."""
        return KeyError(
            f"""Multiple hierarchies with name {key}. Specify the dimension: {", ".join([
            f'cube.hierarchies["{hierarchy.dimension}", "{hierarchy.name}"]'
            for hierarchy in hierarchies
        ])}"""
        )
