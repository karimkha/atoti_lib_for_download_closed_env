from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from ._parsing_utils import Config, convert_path_to_absolute_string


@dataclass(frozen=True)
class BrandingConfig(Config):
    """The UI elements to change in the app to replace the atoti branding with another one.

    Note:
        This feature requires the :mod:`atoti-plus <atoti_plus>` plugin.

    Example:

        >>> config = {
        ...     "branding": {
        ...         "favicon": "favicon.ico",
        ...         "logo": "../logo.svg",
        ...         "title": "Analytic App",
        ...     }
        ... }

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    favicon: Optional[Union[Path, str]] = None
    """The file path to a ``.ico`` image that will be used as the favicon."""

    logo: Optional[Union[Path, str]] = None
    """The file path to a 24px by 24px ``.svg`` image that will be displayed in the upper-left corner."""

    title: Optional[str] = None
    """The title to give to the browser tab (in the home page)."""

    def __post_init__(self) -> None:
        convert_path_to_absolute_string(self, "favicon", "logo")
