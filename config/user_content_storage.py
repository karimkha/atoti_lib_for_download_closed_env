from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
from warnings import warn

from .._jdbc_utils import normalize_jdbc_url
from .._path_utils import to_absolute_path
from .._plugins import ensure_plugin_active
from ._parsing_utils import Config


def _is_remote_url(user_content_storage_url: str):
    return user_content_storage_url.startswith(
        "http://"
    ) or user_content_storage_url.startswith("https://")


def _local_path_to_h2_url(user_content_storage_url: Union[Path, str]):  # type: ignore
    absolute_path = to_absolute_path(Path(user_content_storage_url) / "content")
    return f"jdbc:h2:file:{absolute_path}"


def _resolve_user_content_storage_url(user_content_storage_url: str) -> str:
    if _is_remote_url(user_content_storage_url):
        warn(
            "Using remote content servers via HTTP(S) is deprecated. Use a JDBC server instead.",
            category=FutureWarning,
            stacklevel=2,
        )
        return user_content_storage_url
    return normalize_jdbc_url(user_content_storage_url)


def _infer_driver_class(url: str) -> str:
    ensure_plugin_active("sql")
    from atoti_sql._driver_utils import infer_driver

    return infer_driver(url)


@dataclass(frozen=True)
class UserContentStorageConfig(Config):
    """The advanced configuration for the user content storage.

    Note:
        JDBC backed user content storage requires the :mod:`atoti-sql <atoti_sql>` plugin.

    Example:

        >>> config = {
        ...     "user_content_storage": {
        ...         "url": "mysql://localhost:7777/example?user=username&password=passwd"
        ...     }
        ... }

        .. doctest::
            :hide:

            >>> validate_config(config)

        For drivers not embedded with :mod:`atoti-sql <atoti_sql>`, extra JARs can be passed:

        >>> import glob
        >>> config = {
        ...     "user_content_storage": {
        ...         "url": "jdbc:bigquery://https://www.googleapis.com/bigquery/v2:443;ProjectId=PROJECT_ID;OAuthType=0;OAuthServiceAcctEmail=EMAIL_OF_SERVICEACCOUNT;OAuthPvtKeyPath=path/to/json/keys;",
        ...         "driver": "com.simba.googlebigquery.jdbc42.Driver",
        ...     },
        ...     "extra_jars": glob.glob("./odbc_jdbc_drivers/*.jar"),
        ... }

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    url: str
    """The JDBC connection URL of the database.

    The ``jdbc:`` prefix is optional but the database specific part (such as ``h2:`` or ``mysql:``) is mandatory.
    For instance:

        * ``h2:file:/home/user/database/file/path;USER=username;PASSWORD=passwd``
        * ``mysql://localhost:7777/example?user=username&password=passwd``
        * ``postgresql://postgresql.db.server:5430/example?user=username&password=passwd``

    More examples can be found `here <https://www.baeldung.com/java-jdbc-url-format>`__.
    """

    driver: Optional[str] = None
    """The JDBC driver used to load the data.

    If ``None``, the driver is inferred from the URL.
    Drivers can be found in the :mod:`atoti_sql.drivers` module.
    """

    def __post_init__(self) -> None:
        self.__dict__["url"] = _resolve_user_content_storage_url(self.url)

        if not _is_remote_url(self.__dict__["url"]) and self.driver is None:
            self.__dict__["driver"] = _infer_driver_class(str(self.url))
