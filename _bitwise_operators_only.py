from __future__ import annotations

from abc import ABC
from typing import Any, Tuple, Union

IdentityElement = Union[str, int, float]


class BitwiseOperatorsOnly(ABC):
    """Instances of this class cannot be auto casted to booleans but can be combined with bitwise operators."""

    def _bool_error_message(self) -> str:
        """Return the error message to be used if a boolean auto casting is applied to this object."""
        alternative_message = self._get_bool_alternative_message()
        return f"A {self.__class__.__name__} cannot be cast to a boolean." + (
            "" if len(alternative_message) == 0 else " " + alternative_message
        )

    def _get_bool_alternative_message(self) -> str:  # pylint: disable=no-self-use
        """Return the message explaining what is the boolean alternative for this class."""
        return ""

    def _identity(self) -> Tuple[IdentityElement, ...]:
        """Return a tuple representing the identity of this class.

        Two instances with the same identity tuples are considered equal.
        """
        raise TypeError(f"a {self.__class__.__name__} has no defined identity")

    def __eq__(self, other: Any) -> Any:
        if not isinstance(other, self.__class__):
            return False
        return self._identity() == other._identity()

    def __ne__(self, other: Any) -> Any:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((str(self.__class__),) + self._identity())

    def __bool__(self) -> Any:
        """Prevent boolean auto casting."""
        raise TypeError(self._bool_error_message())
