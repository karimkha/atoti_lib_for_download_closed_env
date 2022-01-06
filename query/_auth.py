from base64 import b64encode

from .auth import Auth


def create_basic_authentication(username: str, password: str) -> Auth:
    """Create a basic authentication."""
    plain_credentials = f"{username}:{password}"
    encoded_credentials = str(b64encode(plain_credentials.encode("ascii")), "utf8")
    http_headers = {"Authorization": f"Basic {encoded_credentials}"}
    return lambda url: http_headers


def create_token_authentication(token: str) -> Auth:
    """Create an authentication based on a Bearer token.

    Args:
        token: The token to use to authenticate, such as a JWT.
    """
    http_headers = {"Authorization": f"Bearer {token}"}
    return lambda url: http_headers
