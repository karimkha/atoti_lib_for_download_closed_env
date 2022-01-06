from dataclasses import dataclass

from .._base._base_level import BaseLevel
from .._repr_utils import ReprJson


@dataclass(eq=False)
class QueryLevel(BaseLevel):
    """Level of a query cube."""

    _dimension: str
    _hierarchy: str

    @property
    def dimension(self) -> str:
        return self._dimension

    @property
    def hierarchy(self) -> str:
        return self._hierarchy

    def _repr_json_(self) -> ReprJson:
        data = {
            "dimension": self.dimension,
            "hierarchy": self.hierarchy,
        }
        return (
            data,
            {"expanded": True, "root": self.name},
        )
