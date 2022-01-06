from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class HttpRequest:
    """Info of an HTTP request."""

    url: str
    """URL on which the client request was made."""

    path_parameters: Mapping[str, str]
    """Mapping from the name of the path parameters to their value for this request."""

    body: Optional[Any]
    """Parsed JSON body of the request."""
