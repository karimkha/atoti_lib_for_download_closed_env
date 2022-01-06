import os
from distutils.util import strtobool


def get_env_flag(variable_name: str) -> bool:
    result = strtobool(
        os.environ.get(
            variable_name,
            # The default is not configurable because it's simpler if the absence of the flag is equivalent to it being false.
            default="False",
        )
    )
    # strtobool's type annotations indicate that it returns a bool but it actually returns 0 or 1.
    # Converting it to a real bool so that `is True` or `is False` can be used down the road.
    return bool(result)
