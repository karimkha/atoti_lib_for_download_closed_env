from __future__ import annotations

import operator
from abc import abstractmethod
from dataclasses import dataclass, field
from itertools import chain
from typing import Dict, Generic, Iterator, Mapping, Optional, Tuple, TypeVar, Union

from typeguard import typeguard_ignore

from .._ipython_utils import ipython_key_completions_for_mapping
from .._repr_utils import ReprJson, ReprJsonable
from ._base_hierarchies import BaseHierarchies
from ._base_level import BaseLevel

_LevelKey = Union[str, Tuple[str, str], Tuple[str, str, str]]
_BaseLevel = TypeVar("_BaseLevel", bound="BaseLevel")
_BaseHierarchies = TypeVar("_BaseHierarchies", bound="BaseHierarchies")


@typeguard_ignore
@dataclass(frozen=True)
class BaseLevels(
    Generic[_BaseLevel, _BaseHierarchies], Mapping[_LevelKey, _BaseLevel], ReprJsonable
):
    """Base class to manipulate flattened levels."""

    _hierarchies: _BaseHierarchies = field(repr=False)

    def _flatten(self) -> Dict[str, Optional[_BaseLevel]]:
        flat_levels: Dict[str, Optional[_BaseLevel]] = {}
        for hierarchy in self._hierarchies.values():
            for level in hierarchy.levels.values():
                if level.name in flat_levels:
                    # None is used as a flag to mark levels appearing in multiple hiearchies.
                    # When it happens, the user must use a tuple to retrieve the level.
                    # Like that: (hierarchy name, level name).
                    flat_levels[level.name] = None
                else:
                    flat_levels[level.name] = level
        return flat_levels

    def __getitem__(self, key: _LevelKey) -> _BaseLevel:
        """Return the level with the given key."""
        if isinstance(key, str):
            return self._find_level(key)

        if len(key) == 2:
            return self._find_level(key[1], hierarchy_name=key[0])

        return self._find_level(key[2], dimension_name=key[0], hierarchy_name=key[1])

    @abstractmethod
    def _find_level(
        self,
        level_name: str,
        *,
        dimension_name: Optional[str] = None,
        hierarchy_name: Optional[str] = None,
    ) -> _BaseLevel:
        """Get a level from the hierarchy name and level name."""

    def __iter__(
        self,
    ) -> Iterator[_BaseLevel]:  # pyright: reportIncompatibleMethodOverride=false
        """Return the iterator on all the levels."""
        # Pyright can't match the type in the comprehension
        return chain(  # type: ignore
            *[
                iter(
                    {
                        (hierarchy.name, level_name): level
                        for level_name, level in hierarchy.levels.items()
                    }
                )
                for hierarchy in self._hierarchies.values()
            ]
        )

    def __len__(self) -> int:
        """Return the number of levels."""
        return sum([len(hierarchy.levels) for hierarchy in self._hierarchies.values()])

    def _ipython_key_completions_(self):
        return ipython_key_completions_for_mapping(self._flatten())

    def _repr_json_(self) -> ReprJson:
        # Use the dimension/hierarchy/level in the map key to make it unique.
        data = {
            f"{level.name} ({level.dimension}/{level.hierarchy}/{level.name})": level._repr_json_()[
                0
            ]
            for hierarchy in self._hierarchies.values()
            for level in hierarchy.levels.values()
        }
        sorted_data = dict(sorted(data.items(), key=operator.itemgetter(0)))
        return (
            sorted_data,
            {
                "expanded": True,
                "root": "Levels",
            },
        )
