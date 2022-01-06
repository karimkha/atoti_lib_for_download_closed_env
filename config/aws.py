from dataclasses import dataclass
from typing import Any, Mapping, Optional

from ._parsing_utils import Config, pop_optional_sub_config
from .key_pair import KeyPairConfig


@dataclass(frozen=True)
class AwsKmsConfig(Config):
    """The KMS configuration to use for client side encryption.

    The AWS KMS CMK must have been created in the same AWS region as the destination bucket (Cf. `AWS documentation <https://docs.aws.amazon.com/AmazonS3/latest/dev/replication-config-for-kms-objects.html>`__).

    Example:

        >>> config = {
        ...     "aws": {
        ...         "client_side_encryption": {"kms": {"key_id": "some key ID"}},
        ...         "region": "us-east-1",
        ...     }
        ... }

        .. doctest::
            :hide:

            >>> validate_config(config)

    """

    key_id: str
    """The ID to identify the key in KMS."""


@dataclass(frozen=True)
class AwsClientSideEncryptionConfig(Config):
    """The `client side encryption <https://docs.aws.amazon.com/AmazonS3/latest/dev/UsingClientSideEncryption.html>`__ configuration to use when loading data from AWS."""

    key_pair: Optional[KeyPairConfig] = None
    """The key pair to use for client side encryption.

        Example:

            >>> config = {
            ...     "aws": {
            ...         "client_side_encryption": {
            ...             "key_pair": {
            ...                 "public_key": "some public key",
            ...                 "private_key": "some private key",
            ...             }
            ...         },
            ...         "region": "us-east-1",
            ...     }
            ... }

            .. doctest::
                :hide:

                >>> validate_config(config)

    """

    kms: Optional[AwsKmsConfig] = None

    @classmethod
    def _from_mapping(cls, mapping: Mapping[str, Any]):
        data = dict(mapping)
        return cls(
            key_pair=pop_optional_sub_config(
                data, attribute_name="key_pair", sub_config_class=KeyPairConfig
            ),
            kms=pop_optional_sub_config(
                data, attribute_name="kms", sub_config_class=AwsKmsConfig
            ),
            **data,
        )

    def __post_init__(self) -> None:
        configured_mechanisms = [
            value for value in self.__dict__.values() if value is not None
        ]

        if not configured_mechanisms:
            raise ValueError("No AWS client side encryption mechanism configured.")

        if len(configured_mechanisms) > 1:
            raise ValueError(
                "Only a single AWS client side encryption mechanism can be configured."
            )


@dataclass(frozen=True)
class AwsConfig(Config):
    """The AWS configuration.

    Note:
        This requires the :mod:`atoti-aws <atoti_aws>` plugin.

    Warning:
        Deprecated, use :func:`~atoti_aws.create_aws_key_pair` or :func:`~atoti_aws.create_aws_kms_config` instead.
    """

    region: str
    """The AWS region to interact with."""

    client_side_encryption: Optional[AwsClientSideEncryptionConfig] = None

    @classmethod
    def _from_mapping(cls, mapping: Mapping[str, Any]):
        data = dict(mapping)
        return cls(
            client_side_encryption=pop_optional_sub_config(
                data,
                attribute_name="client_side_encryption",
                sub_config_class=AwsClientSideEncryptionConfig,
            ),
            **data,
        )
