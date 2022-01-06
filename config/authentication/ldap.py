from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from ..._deprecation import deprecated
from .._parsing_utils import Config


@dataclass(frozen=True)
class LdapConfig(Config):
    """The configuration to connect to an `LDAP <https://en.wikipedia.org/wiki/Lightweight_Directory_Access_Protocol>`__ authentication provider.

    The user's roles are defined using :class:`~atoti_plus.security.LdapSecurity`.

    Example:

        >>> config = {
        ...     "authentication": {
        ...         "ldap": {
        ...             "url": "ldap://example.com:389",
        ...             "base_dn": "dc=example,dc=com",
        ...             "user_search_base": "ou=people",
        ...             "group_search_base": "ou=roles",
        ...         }
        ...     }
        ... }

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    url: str
    """The LDAP URL including the protocol and port."""

    base_dn: str
    """The Base Distinguished Name of the directory service."""

    user_search_filter: str = "(uid={0})"
    """The LDAP filter used to search for users.

    The substituted parameter is the user's login name.
    """

    user_search_base: str = ""
    """Search base for user searches."""

    group_search_filter: str = "(uniqueMember={0})"
    """The LDAP filter to search for groups.

    The substituted parameter is the DN of the user.
    """

    group_search_base: str = ""
    """The search base for group membership searches."""

    group_role_attribute_name: str = "cn"
    """The attribute name that maps a group to a role."""

    role_mapping: Optional[Mapping[str, Iterable[str]]] = None
    """The mapping between the roles returned by the LDAP authentication provider and the corresponding roles to use in atoti.

    LDAP roles are case insensitive.

    Users without the role :guilabel:`ROLE_USER` will not have access to the application.

    Warning:
        This configuration option is deprecated.
        Use :attr:`atoti_plus.security.LdapSecurity.role_mapping` instead.
    """

    def __post_init__(self) -> None:
        if self.__dict__["role_mapping"] is not None:
            deprecated(
                "Setting the role_mapping in the config is deprecated, use LdapSecurity.role_mapping instead."
            )
