from __future__ import annotations

from typing import Dict

from ..._local_session import LocalSession
from ...config import SessionConfig
from .cube import DistributedCube
from .cubes import DistributedCubes


class DistributedSession(LocalSession[DistributedCubes]):
    """Holds a connection to the Java gateway."""

    def __init__(
        self,
        name: str,
        *,
        config: SessionConfig,
        detached_process: bool,
    ):
        """Create the session and the Java gateway."""
        super().__init__(
            name, config=config, detached_process=detached_process, distributed=True
        )
        self._cubes = DistributedCubes(self)

    def __enter__(self) -> DistributedSession:
        """Enter this session's context manager.

        Returns:
            self: to assign it to the "as" keyword.

        """
        return self

    @property
    def cubes(self) -> DistributedCubes:
        """Cubes of the session."""
        return self._cubes

    def create_cube(self, name: str) -> DistributedCube:
        """Create a distributed cube.

        Args:
            name: The name of the created cube.
        """
        self._java_api.create_distributed_cube(name)
        self._java_api.java_api.refresh()
        return DistributedCube(java_api=self._java_api, name=name, session=self)

    def _retrieve_cube(self, cube_name: str) -> DistributedCube:
        java_cube = self._java_api.retrieve_cube(cube_name)
        return DistributedCube(
            java_api=self._java_api,
            name=java_cube.getName(),
            session=self,
        )

    def _retrieve_cubes(self) -> Dict[str, DistributedCube]:
        return {
            java_cube.getName(): DistributedCube(
                java_api=self._java_api, name=java_cube.getName(), session=self
            )
            for java_cube in self._java_api.retrieve_cubes()
        }
