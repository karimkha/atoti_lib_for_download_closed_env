from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

from .._bitwise_operators_only import IdentityElement


@dataclass
class BaseMeasure:
    """Measure of a base cube."""

    _name: str

    @property
    def name(self) -> str:
        """Name of the measure."""
        return self._name

    @property
    @abstractmethod
    def folder(self) -> Optional[str]:
        """Folder of the measure."""

    @property
    @abstractmethod
    def visible(self) -> bool:
        """Whether the measure is visible or not."""

    @property
    @abstractmethod
    def description(self) -> Optional[str]:
        """Description of the measure."""

    @property
    @abstractmethod
    def formatter(self) -> Optional[str]:
        """Formatter of the measure."""

    def _identity(self) -> Tuple[IdentityElement, ...]:
        return (self.name,)
