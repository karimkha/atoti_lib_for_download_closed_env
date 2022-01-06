from dataclasses import dataclass


@dataclass(frozen=True)
class ClientSideEncryption:
    """Parameters to use for client side encryption.

    The following client side encryptions are supported:

        * :mod:`atoti-aws <atoti_aws>` plugin:

            * :func:`~atoti_aws.create_aws_key_pair`.
            * :func:`~atoti_aws.create_aws_kms_config`.

        * :mod:`atoti-azure <atoti_azure>` plugin :

            * :func:`~atoti_azure.create_azure_key_pair`.

    """
