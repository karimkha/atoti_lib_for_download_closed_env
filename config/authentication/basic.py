from dataclasses import dataclass
from typing import Optional

from .._parsing_utils import Config


@dataclass(frozen=True)
class BasicAuthenticationConfig(Config):
    """The `Basic Authentication <https://en.wikipedia.org/wiki/Basic_access_authentication>`__ configuration.

    It is the easiest way to set up security since it only requires defining the users, their password, and their roles using :class:`~atoti_plus.security.BasicSecurity`.
    """

    realm: Optional[str] = None
    """The realm describing the protected area.

    Different realms can be used to isolate sessions running on the same domain (regardless of the port).
    The realm will also be displayed by the browser when prompting for credentials.
    Defaults to ``f"{session_name} atoti session at {session_id}"``.

    Example:

        >>> config = {"authentication": {"basic": {"realm": "Example"}}}

        .. doctest::
            :hide:

            >>> validate_config(config)

    """
