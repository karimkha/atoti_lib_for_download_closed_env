from dataclasses import dataclass
from typing import Mapping, TypeVar

from .._repr_utils import ReprJson, ReprJsonable
from ._base_cube import BaseCube

_BaseCube = TypeVar("_BaseCube", bound="BaseCube")


@dataclass(frozen=True)
class BaseCubes(Mapping[str, _BaseCube], ReprJsonable):
    """Manage the cubes of the session."""

    def _repr_json_(self) -> ReprJson:
        """Return the JSON representation of cubes."""
        return (
            {name: cube._repr_json_()[0] for name, cube in sorted(self.items())},
            {"expanded": False, "root": "Cubes"},
        )
