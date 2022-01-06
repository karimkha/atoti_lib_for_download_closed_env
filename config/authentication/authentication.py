from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .._parsing_utils import Config, pop_optional_sub_config
from .basic import BasicAuthenticationConfig
from .kerberos import KerberosConfig
from .ldap import LdapConfig
from .oidc import OidcConfig


@dataclass(frozen=True)
class AuthenticationConfig(Config):
    """The configuration of the authentication mechanism used by the server to know which users are allowed to connect to the application and which roles they are granted.

    Note:
       This requires the :mod:`atoti-plus <atoti_plus>` plugin.

    If any non-:attr:`basic` authentication is configured, basic authentication will be automatically enabled as well to make it easier to create service/technical users.

    Roles and restrictions can be configured using :class:`atoti_plus.security.Security`.
    """

    basic: Optional[BasicAuthenticationConfig] = None
    kerberos: Optional[KerberosConfig] = None
    ldap: Optional[LdapConfig] = None
    oidc: Optional[OidcConfig] = None

    @classmethod
    def _from_mapping(cls, mapping: Mapping[str, Any]):
        data = dict(mapping)
        return cls(
            basic=pop_optional_sub_config(
                data, attribute_name="basic", sub_config_class=BasicAuthenticationConfig
            ),
            kerberos=pop_optional_sub_config(
                data, attribute_name="kerberos", sub_config_class=KerberosConfig
            ),
            ldap=pop_optional_sub_config(
                data, attribute_name="ldap", sub_config_class=LdapConfig
            ),
            oidc=pop_optional_sub_config(
                data, attribute_name="oidc", sub_config_class=OidcConfig
            ),
            **data,
        )

    def __post_init__(self) -> None:
        configured_mechanisms = [
            value for value in self.__dict__.values() if value is not None
        ]

        if not configured_mechanisms:
            raise ValueError("No authentication mechanism configured.")

        if len(configured_mechanisms) > 1:
            raise ValueError(
                "Only a single authentication mechanism can be configured."
            )
