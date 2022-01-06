import os
from pathlib import Path
from typing import Union

from ._plugins import ensure_plugin_active

PathLike = Union[str, Path]
S3_IDENTIFIER = "s3://"
AZURE_BLOB_IDENTIFIER = ".blob.core.windows.net/"
GCP_IDENTIFIER = "gs://"


def _is_cloud_path(path: str) -> bool:
    """Check whether a path is a supported cloud path or not."""
    return path.startswith((S3_IDENTIFIER, GCP_IDENTIFIER)) or (
        AZURE_BLOB_IDENTIFIER in path
    )


def get_atoti_home() -> Path:
    """Get the path from $ATOTI_HOME env variable. If not defined, use $HOME/.atoti."""
    return Path(os.environ.get("ATOTI_HOME", Path.home() / ".atoti"))


def stem_path(path: PathLike) -> str:
    """Return the final path component, without its suffix."""
    if isinstance(path, Path):
        return path.stem

    if _is_cloud_path(path):
        return stem_path(Path(path[path.rfind("/") + 1 :]))
    return stem_path(Path(path))


def to_absolute_path(path: PathLike) -> str:
    """Transform the input path-like object into an absolute path.

    Args:
        path: A path-like object that points either to a local file or an AWS S3 file.
    """
    if isinstance(path, Path):
        # resolve is for symbolic links.
        # absolute is necessary on Windows to get the actual absolute path.
        return str(path.resolve().absolute())

    if _is_cloud_path(path):
        return path
    return str(Path(path).resolve().absolute())


def to_posix_path(path: PathLike) -> str:
    """Transform the input path-like object into a posix path.

    Args:
        path: A path-like object that points either to a local file or an AWS file.
    """
    if isinstance(path, Path):
        return str(path.as_posix())

    if path.startswith(S3_IDENTIFIER):
        ensure_plugin_active("aws")
        return path
    if AZURE_BLOB_IDENTIFIER in path:
        ensure_plugin_active("azure")
        return path
    if path.startswith(GCP_IDENTIFIER):
        ensure_plugin_active("gcp")
        return path

    # Do not resolve the path yet as it can contain a glob pattern that pathlib._WindowsFlavour does not support.
    # See also: https://github.com/python/cpython/pull/17
    return str(Path(path).as_posix())
