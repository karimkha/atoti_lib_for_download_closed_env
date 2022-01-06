from pathlib import Path
from shutil import copytree, ignore_patterns
from typing import Union

_TUTORIAL_DIRECTORY = Path(Path(__file__).parent) / "tutorial"


def copy_tutorial(path: Union[Path, str]) -> None:
    """Copy the tutorial files to the given path."""
    copytree(_TUTORIAL_DIRECTORY, path, ignore=ignore_patterns(".ipynb_checkpoints"))
