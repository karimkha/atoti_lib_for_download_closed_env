from dataclasses import dataclass

from ._parsing_utils import Config


@dataclass(frozen=True)
class KeyPairConfig(Config):
    public_key: str
    """The public key."""

    private_key: str
    """The private key."""
