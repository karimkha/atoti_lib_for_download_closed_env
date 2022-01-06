from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping, TypeVar

from ._base._base_cubes import BaseCubes
from ._ipython_utils import ipython_key_completions_for_mapping
from ._local_cube import LocalCube
from ._mappings import DelegateMutableMapping

if TYPE_CHECKING:
    from ._local_session import LocalSession

_LocalCube = TypeVar("_LocalCube", bound="LocalCube", covariant=True)


@dataclass(frozen=True)
class LocalCubes(DelegateMutableMapping[str, _LocalCube], BaseCubes[_LocalCube]):
    """Local cubes class."""

    _session: LocalSession[LocalCubes[_LocalCube]] = field(repr=False)

    def _update(  # pylint: disable=no-self-use
        self, mapping: Mapping[str, _LocalCube]
    ) -> None:
        raise RuntimeError(
            "The cubes cannot be updated like this. Use Session.create_cube() instead."
        )

    def __delitem__(self, key: str) -> None:
        """Delete the cube with the given name."""
        try:
            self._session._java_api.delete_cube(key)
            self._session._java_api.refresh()
        except KeyError:
            raise Exception(f"No cube named {key}") from None

    def _ipython_key_completions_(self):
        return ipython_key_completions_for_mapping(self)
