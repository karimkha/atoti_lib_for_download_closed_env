import argparse
from pathlib import Path

from typing_extensions import Final

from ._tutorial import copy_tutorial

if __name__ == "__main__":
    parser: Final = argparse.ArgumentParser(  # pylint: disable=invalid-name
        description="Copy the tutorial files."
    )
    parser.add_argument(
        "path",
        help="the path where the tutorial files will be copied to",
        type=str,
    )
    args: argparse.Namespace = parser.parse_args()
    copy_tutorial(args.path)
    print(f"The tutorial files have been copied to {str(Path(args.path).resolve())}")
