import json
import os
from datetime import datetime
from pathlib import Path
from subprocess import STDOUT, CalledProcessError, check_output  # nosec
from typing import Tuple

from ._compatibility import check_java_version

_ATOTI_JAVA_HOME_ENVIRONMENT_VARIABLE = "ATOTI_JAVA_HOME"
_JAVA_HOME_ENVIRONMENT_VARIABLE = "JAVA_HOME"

JAR_PATH = Path(__file__).parent / "data" / "atoti.jar"


def get_java_path(*, executable_name: str = "java") -> Path:
    """Get the path to the Java executable.

    Uses the first available of:

    * $ATOTI_JAVA_HOME/bin/java
    * jdk4py
    * $JAVA_HOME/bin/java
    * java

    """
    if _ATOTI_JAVA_HOME_ENVIRONMENT_VARIABLE in os.environ:
        return (
            Path(os.environ[_ATOTI_JAVA_HOME_ENVIRONMENT_VARIABLE])
            / "bin"
            / executable_name
        )
    try:
        from jdk4py import JAVA_HOME

        return JAVA_HOME / "bin" / executable_name
    except ImportError:
        java_path = (
            Path(os.environ[_JAVA_HOME_ENVIRONMENT_VARIABLE]) / "bin" / executable_name
            if _JAVA_HOME_ENVIRONMENT_VARIABLE in os.environ
            else Path(executable_name)
        )
        return java_path


def retrieve_info_from_jar() -> Tuple[datetime, bool]:
    """Retrieve info from the embedded JAR."""
    java_path = get_java_path()
    check_java_version((11,), java_path=java_path)

    try:
        output = check_output(
            [str(java_path), "-jar", str(JAR_PATH), "--info"], stderr=STDOUT, text=True
        )
    except CalledProcessError as error:
        raise RuntimeError(f"Could not retrieve JAR info:\n{error.output}") from error

    try:
        info = json.loads(output.strip().splitlines()[-1])
        return (
            datetime.fromtimestamp(int(info["licenseEndDate"]) / 1000),
            info["isCommunityLicense"],
        )
    except Exception as error:
        raise RuntimeError(
            f"Could not process JAR info from output:\n{output}"
        ) from error
