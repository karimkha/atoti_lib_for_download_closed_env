from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, TypeVar

from typeguard import typechecked, typeguard_ignore

from atoti.query.measure import QueryMeasure

from ._base._base_measures import BaseMeasures
from ._mappings import DelegateMutableMapping
from .measure import Measure

if TYPE_CHECKING:
    from ._java_api import JavaApi

_Measure = TypeVar("_Measure", Measure, QueryMeasure)


@typeguard_ignore
@dataclass
class LocalMeasures(DelegateMutableMapping[str, _Measure], BaseMeasures[_Measure]):
    """Local measures class."""

    _java_api: JavaApi = field(repr=False)

    @abstractmethod
    def _get_underlying(self) -> Dict[str, _Measure]:
        """Fetch the measures from the JVM each time they are needed."""

    @typechecked
    @abstractmethod
    def __getitem__(self, key: str) -> _Measure:
        """Return the measure with the given name."""

    @typechecked
    @abstractmethod
    def __delitem__(self, key: str) -> None:
        """Delete a measure.

        Args:
            key: The name of the measure to delete.
        """
