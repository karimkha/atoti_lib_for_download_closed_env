from abc import abstractmethod
from dataclasses import dataclass
from typing import (
    Dict,
    Generic,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    MutableMapping,
    Tuple,
    TypeVar,
    Union,
    ValuesView,
)

from ._ipython_utils import ipython_key_completions_for_mapping

_Key = TypeVar("_Key")
_Value = TypeVar("_Value")


@dataclass(frozen=True)
class ImmutableMapping(Generic[_Key, _Value], Mapping[_Key, _Value]):
    """Immutable mapping."""

    __data: Mapping[_Key, _Value]

    def __getitem__(self, key: _Key) -> _Value:
        """Get the value with the given key."""
        return self.__data[key]

    def __iter__(self) -> Iterator[_Key]:
        """Return the iterator on elements."""
        return iter(self.__data)

    def __len__(self) -> int:
        """Return the number of elements."""
        return len(self.__data)

    def __repr__(self) -> str:
        return repr(self.__data)

    def _ipython_key_completions_(self):
        return ipython_key_completions_for_mapping(self)  # type: ignore


EMPTY_MAPPING = ImmutableMapping({})


class DelegateMutableMapping(Generic[_Key, _Value], MutableMapping[_Key, _Value]):
    """Mutable mapping backed by an underlying mapping.

    Reimplement keys, items, and values methods for performance reasons.
    See https://github.com/activeviam/atoti/pull/1162#issuecomment-592551497

    """

    @abstractmethod
    def _get_underlying(self) -> Dict[_Key, _Value]:
        """Get the underlying mapping."""

    @abstractmethod
    def _update(self, mapping: Mapping[_Key, _Value]):
        ...

    # pylint: disable=arguments-differ

    def update(  # type:ignore
        self,
        other: Union[Mapping[_Key, _Value], Iterable[Tuple[_Key, _Value]]],
        **kwargs: _Value
    ) -> None:

        """Update the mapping."""
        full_mapping = {}
        full_mapping.update(other, **kwargs)
        self._update(full_mapping)

    # pylint: enable=arguments-differ

    def __setitem__(self, key: _Key, value: _Value) -> None:
        self.update({key: value})

    def __getitem__(self, key: _Key) -> _Value:
        return self._get_underlying()[key]

    def __iter__(self) -> Iterator[_Key]:
        """Return the mapping's iterator."""
        return iter(self._get_underlying())

    def __len__(self) -> int:
        """Return the number of items."""
        return len(self._get_underlying())

    def keys(self) -> KeysView[_Key]:
        """Return a set-like object providing a view on the keys."""
        return self._get_underlying().keys()

    def items(self) -> ItemsView[_Key, _Value]:
        """Return a set-like object providing a view on the items."""
        return self._get_underlying().items()

    def values(self) -> ValuesView[_Value]:
        """Return an object providing a view on the values."""
        return self._get_underlying().values()

    def _ipython_key_completions_(self):
        return ipython_key_completions_for_mapping(self)  # type: ignore
