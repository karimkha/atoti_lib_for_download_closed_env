from dataclasses import dataclass
from typing import Optional

from .._base._base_measure import BaseMeasure


@dataclass
class QueryMeasure(BaseMeasure):
    """Measure of a query cube."""

    _visible: bool
    _folder: Optional[str]
    _formatter: Optional[str]
    _description: Optional[str]

    @property
    def folder(self) -> Optional[str]:
        return self._folder

    @property
    def visible(self) -> bool:
        return self._visible

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def formatter(self) -> Optional[str]:
        return self._formatter
