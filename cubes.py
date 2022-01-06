from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict

from typeguard import typeguard_ignore

from ._local_cubes import LocalCubes
from .cube import Cube

if TYPE_CHECKING:
    from .session import Session


@typeguard_ignore
@dataclass(frozen=True)
class Cubes(LocalCubes[Cube]):
    """Manage the cubes of the session."""

    _session: Session = field(repr=False)

    def __getitem__(self, key: str) -> Cube:
        """Get the cube with the given name."""
        return self._session._retrieve_cube(key)

    def _get_underlying(self) -> Dict[str, Cube]:
        return self._session._retrieve_cubes()
