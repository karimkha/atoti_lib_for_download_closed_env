from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict

from typeguard import typeguard_ignore

from ..._local_cubes import LocalCubes
from .cube import DistributedCube

if TYPE_CHECKING:
    from .session import DistributedSession


@typeguard_ignore
@dataclass(frozen=True)
class DistributedCubes(LocalCubes[DistributedCube]):
    """Manage the distributed cubes."""

    _session: DistributedSession = field(repr=False)

    def __getitem__(self, key: str) -> DistributedCube:
        """Get the cube with the given name."""
        return self._session._retrieve_cube(key)

    def _get_underlying(self) -> Dict[str, DistributedCube]:
        return self._session._retrieve_cubes()
