from abc import ABC
from typing import Any, Dict, Mapping, Optional, Type, TypeVar

from .._path_utils import to_absolute_path

ConfigClass = TypeVar("ConfigClass")


class Config(ABC):
    @classmethod
    def _from_mapping(
        cls: Type[ConfigClass], mapping: Mapping[str, Any]
    ) -> ConfigClass:
        """Take a mapping and return an instance of the class."""
        return cls(**mapping)


SubConfig = TypeVar("SubConfig", bound=Config)


def pop_optional_sub_config(
    data: Dict[str, Any], *, attribute_name: str, sub_config_class: Type[SubConfig]
) -> Optional[SubConfig]:
    return (
        sub_config_class._from_mapping(data.pop(attribute_name))
        if attribute_name in data
        else None
    )


def convert_path_to_absolute_string(config: Config, *attribute_names: str):
    for attribute_name in attribute_names:
        attribute_value = getattr(config, attribute_name)
        if attribute_value is not None:
            config.__dict__[attribute_name] = to_absolute_path(attribute_value)
