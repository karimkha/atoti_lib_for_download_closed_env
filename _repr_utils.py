from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Mapping, Tuple, Union

_INDENTATION = "  "

ReprJson = Tuple[Any, Dict[str, Union[bool, str]]]


def _json_to_html(
    obj: Union[Iterable[Any], Mapping[str, Any]], *, indent: int = 0
) -> str:
    return (
        _mapping_to_html(obj, indent=indent)
        if isinstance(obj, Mapping)
        else _iterable_to_html(obj, indent=indent)
    )


def _mapping_to_html(mapping: Mapping[str, Any], *, indent: int = 0) -> str:
    pretty = f"{_INDENTATION * indent}<ul>\n"
    for key, value in mapping.items():
        if isinstance(value, (Iterable, Mapping)) and not isinstance(value, str):
            pretty += f"{_INDENTATION * indent}<li>{key}\n"
            pretty += _json_to_html(value, indent=indent + 1)
            pretty += f"{_INDENTATION * indent}</li>\n"
        else:
            pretty += f"{_INDENTATION * indent}<li>{key}: {value}</li>\n"
    return f"{pretty}{_INDENTATION * indent}</ul>\n"


def _iterable_to_html(iterable: Iterable[Any], *, indent: int = 0) -> str:
    pretty = f"{_INDENTATION * indent}<ol>\n"
    for value in iterable:
        if isinstance(value, (Iterable, Mapping)) and not isinstance(value, str):
            pretty += f"{_INDENTATION * indent}<li>{_json_to_html(value, indent=indent + 1)}</li>\n"
        else:
            pretty += f"{_INDENTATION * indent}<li>{value}</li>\n"
    return f"{pretty}{_INDENTATION * indent}</ol>"


class ReprJsonable(ABC):
    @abstractmethod
    def _repr_json_(self) -> ReprJson:
        """Return the JSON representation of this object."""

    def _repr_html_(self) -> str:
        """Return the HTML representation of this object."""
        repr_json = self._repr_json_()
        metadata = repr_json[1]
        if "root" in metadata:
            obj = {str(repr_json[1]["root"]): repr_json[0]}
        else:
            obj = repr_json[0]
        return _json_to_html(obj)
