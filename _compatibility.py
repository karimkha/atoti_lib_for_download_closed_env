import re
from pathlib import Path
from subprocess import STDOUT, CalledProcessError, check_output  # nosec
from typing import Tuple


def _get_java_version_part(java_version_output: str) -> str:
    """Return the part corresponding to the Java version (e.g. ``"1.8.0_212"``) from the output of the ``java -version`` command."""
    match = re.search(r'\w+ version "(?P<version_part>[^"]+)"', java_version_output)

    if match:
        version_part = match.group("version_part")
        if version_part:
            return version_part

    raise RuntimeError(f"Could not extract version part from:\n{java_version_output}")


def _convert_element_to_int(element: str) -> int:
    try:
        return int(element)
    except ValueError:
        # For elements such as ``"ea"``.
        return -1


def _extract_java_version(java_version_output: str) -> Tuple[int, ...]:
    """Return the version numbers (e.g. ``[11, 0, 2]``) from the output of the ``java -version`` command."""
    version_elements = re.split(r"[._-]", _get_java_version_part(java_version_output))
    return tuple(_convert_element_to_int(element) for element in version_elements)


def check_java_version(minimum_supported_version: Tuple[int], *, java_path: Path):
    try:
        output = check_output(  # nosec
            [str(java_path), "-version"], stderr=STDOUT, text=True
        )
    except CalledProcessError as error:
        raise Exception(f"Cannot retrieve Java version:\n{error.output}") from error

    java_version = _extract_java_version(output)

    if java_version < tuple(minimum_supported_version):
        raise Exception(
            f"Java >= {'.'.join(map(str, minimum_supported_version))} is required but current version is {'.'.join(map(str, java_version))}."
        )
