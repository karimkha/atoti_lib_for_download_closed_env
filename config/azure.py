from dataclasses import dataclass
from typing import Any, Mapping, Optional

from ._parsing_utils import Config, pop_optional_sub_config
from .key_pair import KeyPairConfig


@dataclass(frozen=True)
class AzureKeyPair(KeyPairConfig):
    """The key pair to use for client side encryption.

    Warning:

        Each encrypted blob must have the metadata attribute ``unencrypted_content_length`` with the unencrypted file size.
        If this is not set, an :guilabel:`Issue while downloading` error will occur.

    Warning:
        Deprecated, use :func:`~atoti_azure.create_azure_key_pair` instead.

    Example:

        >>> config = {
        ...     "azure": {
        ...         "client_side_encryption": {
        ...             "key_pair": {
        ...                 "key_id": "some key ID",
        ...                 "public_key": "some public key",
        ...                 "private_key": "some private key",
        ...             }
        ...         }
        ...     }
        ... }

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    key_id: str
    """The ID of the key used to encrypt the blob."""


@dataclass(frozen=True)
class AzureClientSideEncryptionConfig(Config):
    """The client side encryption configuration to use when loading data from Azure."""

    key_pair: AzureKeyPair

    @classmethod
    def _from_mapping(cls, mapping: Mapping[str, Any]):
        data = dict(mapping)
        return cls(
            key_pair=AzureKeyPair._from_mapping(data.pop("key_pair")),
            **data,
        )


@dataclass(frozen=True)
class AzureConfig(Config):
    """The Azure configuration.

    Note:
        This requires the :mod:`atoti-azure <atoti_azure>` plugin.

    """

    client_side_encryption: Optional[AzureClientSideEncryptionConfig] = None

    @classmethod
    def _from_mapping(cls, mapping: Mapping[str, Any]):
        data = dict(mapping)
        return cls(
            client_side_encryption=pop_optional_sub_config(
                data,
                attribute_name="client_side_encryption",
                sub_config_class=AzureClientSideEncryptionConfig,
            ),
            **data,
        )
