"""
Warning:
    Experimental features are subject to breaking changes (even removals) in minor and/or patch releases.

atoti supports distributed clusters with several data cubes and one query cube.

This is not the same as a query session: in a query session, the query cube connects to a remote data cube and query its content, while in a distributed setup, multiple data cubes can join a distributed cluster where a distributed cube can be queried to retrieve the union of their data.
"""

from __future__ import annotations

from typing import Any, Mapping

from ..._mappings import EMPTY_MAPPING
from ...cube import Cube
from .session import DistributedSession


def create_distributed_session(
    name: str = "Unnamed", *, config: Mapping[str, Any] = EMPTY_MAPPING, **kwargs: Any
) -> DistributedSession:
    """Create a distributed session."""
    from ... import sessions

    return sessions._create_distributed_session(name, config=config, **kwargs)


def join_distributed_cluster(
    *,
    cube: Cube,
    distributed_session_url: str,
    distributed_cube_name: str,
) -> None:
    """Join the distributed cluster at the given address for the given distributed cube."""
    cube._join_distributed_cluster(distributed_session_url, distributed_cube_name)
