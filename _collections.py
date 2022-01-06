from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Generic, MutableSet, TypeVar

_Item = TypeVar("_Item")


@dataclass(frozen=True)
class DelegateMutableSet(Generic[_Item], MutableSet[_Item]):
    """A Set which calls a method each time its elements are changed."""

    _data: MutableSet[_Item] = field(repr=False)

    @abstractmethod
    def _on_change(self) -> None:
        """Hook called each time the data in the set changes."""

    def __contains__(self, value: object) -> bool:
        return value in self._data

    def add(self, value: _Item) -> None:
        self._data.add(value)
        self._on_change()

    def discard(self, value: _Item) -> None:
        self._data.discard(value)
        self._on_change()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)
