from dataclasses import dataclass
from pathlib import Path
from typing import Union

from ._parsing_utils import Config, convert_path_to_absolute_string


@dataclass(frozen=True)
class HttpsConfig(Config):
    """The PKCS 12 keystore configuration to enable HTTPS on the application.

    Note:
        This requires the :mod:`atoti-plus <atoti_plus>` plugin.

    Note:
        PEM or DER certificates can be `converted to PKCS 12 with OpenSSL <https://stackoverflow.com/questions/56241667/convert-certificate-in-der-or-pem-to-pkcs12/56244685#56244685>`__.

    Example:

        >>> config = {"https": {"certificate": "../cert.p12", "password": "secret"}}

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    certificate: Union[Path, str]
    """The path to the certificate."""

    password: str
    """The password to read the certificate."""

    def __post_init__(self) -> None:
        convert_path_to_absolute_string(self, "certificate")
