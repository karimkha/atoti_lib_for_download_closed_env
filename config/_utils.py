import json
from dataclasses import asdict, replace
from io import TextIOBase
from typing import Optional

from .session_config import SessionConfig


def get_logging_destination_io(config: SessionConfig) -> Optional[TextIOBase]:
    return (
        config.logging.destination
        if config.logging and isinstance(config.logging.destination, TextIOBase)
        else None
    )


def serialize_config_to_json(config: SessionConfig) -> str:
    if get_logging_destination_io(config):
        # The io configured to write the logs to is not serializable and Java does not need it.
        config = replace(config, logging=replace(config.logging, destination=None))

    config_dict = asdict(
        config,
        # Remove keys for which the value is `None` (e.g. deprecated properties).
        dict_factory=lambda items: {
            key: value for key, value in items if value is not None
        },
    )

    return json.dumps(config_dict)
