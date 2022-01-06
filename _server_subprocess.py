from __future__ import annotations

import os
import platform
import random
import re
import string
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen  # nosec
from time import sleep, time
from typing import TYPE_CHECKING, List, Tuple

from ._java_utils import JAR_PATH, get_java_path
from ._path_utils import get_atoti_home, to_absolute_path
from ._plugins import get_active_plugins
from ._stream_capturing_buffer import StreamCapturingBuffer
from .config._utils import get_logging_destination_io

if TYPE_CHECKING:
    from .config import SessionConfig

DEFAULT_HADOOP_PATH = Path(__file__).parent / "bin" / "hadoop-3.2.1"

REGEX = "Py4J server started on port (?P<port>[0-9]+)"


def _create_session_directory() -> Path:
    """Create the directory that will contain the session files."""
    # Generate the directory name using a random string for uniqueness.
    random_string = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    session_directory = get_atoti_home() / f"{str(int(time()))}_{random_string}"

    # Create the session directory and its known sub-folders.
    session_directory.mkdir(parents=True)
    _compute_log_directory(session_directory).mkdir()

    return session_directory


def _compute_log_directory(session_directory: Path) -> Path:
    """Return the path to the logs directory."""
    return session_directory / "logs"


def get_plugin_jar_paths() -> List[str]:
    """Get the JAR paths of the available plugins."""
    return [
        str(plugin.get_jar_path())
        for plugin in get_active_plugins().values()
        if plugin.get_jar_path()
    ]


class ServerSubprocess:
    """A wrapper class to start and manage an atoti server from Python."""

    _capturing_buffer: StreamCapturingBuffer

    def __init__(self, *, config: SessionConfig):
        """Create and start the subprocess."""
        self._config = config

        self._session_directory = _create_session_directory()
        self._subprocess_log_file = (
            None
            if get_logging_destination_io(self._config)
            else _compute_log_directory(self._session_directory) / "subprocess.log"
        )
        (self._process, self.py4j_java_port) = self._start()

    def wait(self) -> None:
        """Wait for the process to terminate.

        This will prevent the Python process to exit unless the Py4J gateway is closed since, in that case, the atoti server will stop itself.
        """
        self._process.wait()
        self._capturing_buffer.stop()
        self._capturing_buffer.join()

    def _start(self) -> Tuple[Popen, int]:
        """Start the atoti server and return a tuple containing the server process and the Py4J port."""
        process = self._create_subprocess()

        if not process.stdout:
            raise RuntimeError("Missing subprocess stdout")

        output_stream = get_logging_destination_io(self._config)

        if not output_stream:
            if not self._subprocess_log_file:
                raise RuntimeError(
                    "Expected subprocess log file when not logging to custom IO."
                )

            output_stream = open(  # pylint: disable=consider-using-with
                self._subprocess_log_file, "wt"
            )

        self._capturing_buffer = StreamCapturingBuffer(
            input_stream=process.stdout, output_stream=output_stream
        )
        self._capturing_buffer.start()

        try:
            java_port = self._await_start()
            self._capturing_buffer.skip_writing_to_buffer()
        except Exception as error:
            process.kill()
            raise error

        return (process, java_port)

    def _create_subprocess(self) -> Popen[str]:
        program_args = [
            str(get_java_path()),
            "-jar",
        ]

        program_args.append(f"-Dserver.session_directory={self._session_directory}")

        if not get_logging_destination_io(self._config):
            program_args.append("-Dserver.logging.disable_console_logging=true")

        if self._config.port is not None:
            program_args.append(f"-Dserver.port={self._config.port}")

        # The user is allowed to pass any options to Java, even dangerous ones.
        program_args.extend(self._config.java_options)

        if platform.system() == "Windows":
            program_args.append(
                f"-Dhadoop.home.dir={to_absolute_path(DEFAULT_HADOOP_PATH)}"
            )
            hadoop_path = to_absolute_path(DEFAULT_HADOOP_PATH / "bin")
            if hadoop_path not in os.environ["PATH"]:
                os.environ["PATH"] = f"{os.environ['PATH']};{hadoop_path}"

        # Put JARs from user config or from plugins into loader path
        jars = [*(self._config.extra_jars), *get_plugin_jar_paths()]
        if len(jars) > 0:
            program_args.append(
                f"-Dloader.path={','.join([to_absolute_path(jar) for jar in jars])}"
            )

        program_args.append(to_absolute_path(JAR_PATH))

        try:
            return Popen(  # pylint: disable=consider-using-with
                program_args,
                stderr=STDOUT,
                stdout=PIPE,
                text=True,
            )  # nosec
        except Exception as error:
            raise RuntimeError(
                f"""Could not start the session.{f" You can check the logs at {self._subprocess_log_file}" if self._subprocess_log_file else ""}""",
            ) from error

    def _await_start(self) -> int:
        """Wait for the server to start and return the Py4J Java port."""
        period = 0.25
        timeout = 60
        attempt_count = round(timeout / period)
        # Wait for the process to start and log the Py4J port.
        for _ in range(1, attempt_count):
            # Look for the started line.
            try:
                match = re.search(REGEX, self._capturing_buffer.get_buffer_value())
                if match:
                    # Server should be ready.
                    return int(match.group("port"))

            except FileNotFoundError:
                # The logs file has not yet been created.
                pass

            # The server is not ready yet.
            # Wait for a bit.
            sleep(period)

        # The inner loop did not return.
        # This means that the server could not be started correctly.
        raise RuntimeError(
            f"Could not start server. Check the logs: {self._subprocess_log_file}"
        )

    @property
    def logs_path(self) -> Path:
        """Path to the server log file."""
        if get_logging_destination_io(self._config):
            raise RuntimeError(
                "Logs have been configured to be written to a specified IO."
            )

        if self._config.logging and self._config.logging.destination:
            if not isinstance(self._config.logging.destination, (str, Path)):
                raise TypeError("Unexpected type of logging destination.")

            return Path(self._config.logging.destination)

        return _compute_log_directory(self._session_directory) / "server.log"
