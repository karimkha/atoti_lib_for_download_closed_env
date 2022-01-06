from dataclasses import dataclass
from io import TextIOBase
from pathlib import Path
from typing import Optional, Union

from .._deprecation import deprecated
from ._parsing_utils import Config, convert_path_to_absolute_string


@dataclass(frozen=True)
class LoggingConfig(Config):
    """The configuration describing how the session logs will be handled.

    Example:

        >>> config = {"logging": {"destination": "./atoti/server.log"}}

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    destination: Optional[Union[Path, str, TextIOBase]] = None
    """The place where the session logs will be written to.

    If ``None``, the logs will be written to ``logs/server.log`` in the session directory under ``$ATOTI_HOME`` (this environment variable itself defaults to ``$HOME/.atoti``).

    Note:
        Unless an instance of :class:`io.TextIOBase` is passed, the rolling policy is:

            * Maximum file size of 10MB.
            * Maximum history of 7 days.

        Once the maximum size is reached, logs are archived following the pattern ``f"{destination}.{date}.{i}.gz"`` where ``date`` is the creation date of the file in the ``yyyy-MM-dd`` format and ``i`` an integer incremented during the day.

    Example:

        To stream the session logs to the Python process' standard output:

        >>> import sys
        >>> config = {"logging": {"destination": sys.stdout}}

        .. doctest::
            :hide:

            >>> validate_config(config)
    """

    file_path: Optional[Union[Path, str]] = None
    """The path of the file where the session logs will be written to.

    Warning:
        This configuration option is deprecated.
        Use :attr:`destination` instead.
    """

    def __post_init__(self) -> None:
        if self.file_path:
            deprecated("file_path is deprecated, use destination instead.")
            self.__dict__["destination"] = self.__dict__["file_path"]
            del self.__dict__["file_path"]

        if isinstance(self.destination, (Path, str)):
            convert_path_to_absolute_string(self, "destination")
