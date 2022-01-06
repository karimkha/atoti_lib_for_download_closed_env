from dataclasses import dataclass
from typing import Collection


@dataclass(frozen=True)
class User:
    """Info of a user calling a custom HTTP endpoint."""

    name: str
    """Name of the user calling the endpoint."""

    roles: Collection[str]
    """Roles of the user calling the endpoint."""
