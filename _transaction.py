from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Type

if TYPE_CHECKING:
    from ._java_api import JavaApi


@dataclass
class Transaction:

    _java_api: JavaApi
    _scenario_name: str

    def __enter__(self) -> None:
        self._java_api.start_transaction(self._scenario_name)

    def __exit__(  # pylint: disable=too-many-positional-parameters
        self,
        exception_type: Optional[Type[BaseException]],
        exception_instance: Optional[BaseException],
        exception_traceback: Optional[TracebackType],
    ) -> None:
        has_succeeded = exception_instance is None
        self._java_api.end_transaction(has_succeeded)
