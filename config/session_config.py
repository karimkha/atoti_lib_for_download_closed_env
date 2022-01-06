from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Union

from typing_extensions import Literal

from .._path_utils import to_absolute_path
from ._parsing_utils import Config, pop_optional_sub_config
from .authentication import AuthenticationConfig
from .aws import AwsConfig
from .azure import AzureConfig
from .branding import BrandingConfig
from .https import HttpsConfig
from .i18n import I18nConfig
from .jwt import JwtConfig
from .logging import LoggingConfig
from .user_content_storage import (
    UserContentStorageConfig,
    _is_remote_url,
    _local_path_to_h2_url,
)


@dataclass(frozen=True)
class SessionConfig(Config):
    """The structure of the configuration expected by the session.

    Sub-classes can be explored for more information on how to use each part of the configuration.
    """

    _app_extensions: Optional[Mapping[str, Union[str, Path]]] = None
    """Extensions to add to the app.

    Example:

        >>> config = {
        ...     "_app_extensions": {
        ...         "custom-extension": "../custom/extension/root-directory/dist"
        ...     }
        ... }

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    authentication: Optional[AuthenticationConfig] = None
    """Configure the authentication mechanism for the app.

    Users and roles are configured using :attr:`atoti.session.Session.security`.
    """

    aws: Optional[AwsConfig] = None

    azure: Optional[AzureConfig] = None

    branding: Optional[BrandingConfig] = None
    """UI elements to change in the app to customize its appearance."""

    extra_jars: Iterable[Union[str, Path]] = ()
    """The paths to the JAR that will be added to the classpath of the Java process when starting the session.

    Example:

        >>> config = {"extra_jars": ["../extra.jar"]}

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    https: Optional[HttpsConfig] = None
    """Provide certificates to enable HTTPS on the app."""

    i18n: Optional[I18nConfig] = None
    """Configure custom translation keys for the app."""

    java_options: Iterable[str] = ()
    """The additional options to pass when starting the Java process (e.g. for optimization or debugging purposes).

    In particular, the ``-Xmx`` option can be set to increase the amount of RAM that the session can use.
    If this option is not specified, the JVM default memory setting is used which is 25% of the machine memory.

    Example:

        >>> config = {"java_options": ["-verbose:gc", "-Xms1g", "-XX:+UseG1GC"]}

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    jwt: Optional[JwtConfig] = None
    """Set the key pair used to validate JWTs when authenticating with the session."""

    logging: Optional[LoggingConfig] = None
    """Configure log storage for the session."""

    port: Optional[int] = None
    """The port on which the session will be exposed.

    Defaults to a random available port.

    Example:

        >>> config = {"port": 8080}

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    same_site: Literal["lax", "none", "strict"] = "lax"
    """The value to use for the *SameSite* attribute of the HTTP cookie sent by the session when :attr:`authentication` is configured.

    Note:
        This requires the :mod:`atoti-plus <atoti_plus>` plugin.

    See https://web.dev/samesite-cookies-explained for more information.

    Setting it to ``none`` requires the session to be served through HTTPS.

    Example:

        >>> config = {"same_site": "strict"}

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    user_content_storage: Optional[Union[Path, str, UserContentStorageConfig]] = None
    """The location of the database where the user content will be stored.

    The user content is what is not part of the data sources, such as the dashboards, widgets, and filters saved in the application.

    Defaults to ``None`` meaning that the user content is kept in memory and is lost when the atoti session is closed.

    If a path to a directory is given, it will be created if needed.

    Example:

        >>> config = {"user_content_storage": "./content"}

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    @classmethod
    def _from_mapping(cls, mapping: Mapping[str, Any]):
        data = dict(mapping)
        return cls(
            authentication=pop_optional_sub_config(
                data,
                attribute_name="authentication",
                sub_config_class=AuthenticationConfig,
            ),
            aws=pop_optional_sub_config(
                data, attribute_name="aws", sub_config_class=AwsConfig
            ),
            azure=pop_optional_sub_config(
                data, attribute_name="azure", sub_config_class=AzureConfig
            ),
            branding=pop_optional_sub_config(
                data, attribute_name="branding", sub_config_class=BrandingConfig
            ),
            https=pop_optional_sub_config(
                data, attribute_name="https", sub_config_class=HttpsConfig
            ),
            i18n=pop_optional_sub_config(
                data, attribute_name="i18n", sub_config_class=I18nConfig
            ),
            jwt=pop_optional_sub_config(
                data, attribute_name="jwt", sub_config_class=JwtConfig
            ),
            logging=pop_optional_sub_config(
                data, attribute_name="logging", sub_config_class=LoggingConfig
            ),
            user_content_storage=_pop_content_storage_config(data),
            **data,
        )

    def __post_init__(self) -> None:
        if self._app_extensions:
            self.__dict__["_app_extensions"] = {
                name: to_absolute_path(path)
                for name, path in self._app_extensions.items()
            }

        self.__dict__["extra_jars"] = [
            to_absolute_path(jar_path) for jar_path in self.extra_jars
        ]


def _pop_content_storage_config(
    data: Dict[str, Any]
) -> Union[str, UserContentStorageConfig, None]:
    if not "user_content_storage" in data:
        return None
    if isinstance(data["user_content_storage"], (str, Path)):
        if isinstance(data["user_content_storage"], str) and _is_remote_url(
            data["user_content_storage"]
        ):
            return UserContentStorageConfig(data.pop("user_content_storage"))
        return UserContentStorageConfig(
            _local_path_to_h2_url(data.pop("user_content_storage")),
            driver="org.h2.Driver",
        )
    return pop_optional_sub_config(
        data,
        attribute_name="user_content_storage",
        sub_config_class=UserContentStorageConfig,
    )
