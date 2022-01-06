from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Tuple

from .._bitwise_operators_only import BitwiseOperatorsOnly, IdentityElement
from .._docs_utils import LEVEL_ISIN_DOC, doc
from .._level_conditions import LevelCondition
from .._level_isin_conditions import LevelIsInCondition
from .._repr_utils import ReprJson, ReprJsonable
from ..measure_description import MeasureDescription


@dataclass(eq=False)
class BaseLevel(ReprJsonable, BitwiseOperatorsOnly):
    """Level of a base cube."""

    _name: str

    @property
    def name(self) -> str:
        """Name of the level."""
        return self._name

    @property
    @abstractmethod
    def dimension(self) -> str:
        """Name of the dimension holding the level."""

    @property
    @abstractmethod
    def hierarchy(self) -> str:
        """Name of the hierarchy holding the level."""

    @property
    def _java_description(self) -> str:  # noqa: D401
        """Description for Java."""
        return f"{self.name}@{self.hierarchy}@{self.dimension}"

    @doc(LEVEL_ISIN_DOC)
    def isin(self, *members: Any) -> LevelIsInCondition:
        if None in members:
            raise ValueError("None is not supported in isin conditions.")
        return LevelIsInCondition(self, list(members))

    @abstractmethod
    def _repr_json_(self) -> ReprJson:
        """JSON representation of the level."""

    def __eq__(
        self, other: Any
    ) -> LevelCondition:  # pyright: reportIncompatibleMethodOverride=false
        """Return an equality condition against this level."""
        if isinstance(other, MeasureDescription):
            return NotImplemented
        return LevelCondition(self, other, "eq")

    def __ne__(
        self, other: Any
    ) -> LevelCondition:  # pyright: reportIncompatibleMethodOverride=false
        """Not supported."""
        # Explicitly implemented so that Python doesn't just silently return False.
        raise NotImplementedError(
            "Query level conditions can only be based on equality (==)."
        )

    # This is needed otherwise errors like "TypeError: unhashable type: 'QueryLevel'" are thrown.
    # This is a "eq=False" dataclass so hash method is generated "according to how eq" is set but
    # the desired behavior is to use BitwiseOperatorsOnly.__hash__().
    def __hash__(self) -> int:  # pylint: disable=useless-super-delegation, no-self-use
        return super().__hash__()

    def _get_bool_alternative_message(self) -> str:  # pylint: disable=no-self-use
        return "For conditions on level members use `isin`, `where` or `filter` method."

    def _identity(self) -> Tuple[IdentityElement, ...]:
        return (self._java_description,)
