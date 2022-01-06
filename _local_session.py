from __future__ import annotations

import logging
from abc import abstractmethod
from datetime import timedelta
from pathlib import Path
from subprocess import STDOUT, CalledProcessError, check_output  # nosec
from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, Optional, Type, TypeVar

from py4j.java_gateway import DEFAULT_PORT as _PY4J_DEFAULT_PORT
from typing_extensions import Literal

from ._base._base_session import BaseSession
from ._deprecation import deprecated
from ._docs_utils import EXPLAIN_QUERY_DOC, doc
from ._endpoint import EndpointHandler
from ._java_api import JavaApi
from ._java_utils import get_java_path
from ._local_cube import LocalCube
from ._local_cubes import LocalCubes
from ._path_utils import PathLike, to_absolute_path
from ._plugins import MissingPluginError, get_active_plugins
from ._query_plan import QueryAnalysis
from ._server_subprocess import ServerSubprocess
from ._type_utils import typecheck
from .client_side_encryption import ClientSideEncryption
from .config import SessionConfig
from .exceptions import AtotiException, AtotiJavaException
from .query._cellset import GetLevelDataTypes
from .query.query_result import QueryResult
from .query.session import _get_query_mdx_doc

if TYPE_CHECKING:
    from ._endpoint import CallbackEndpoint
    from .query.session import QuerySession

_LocalCubes = TypeVar("_LocalCubes", bound="LocalCubes[LocalCube]")


@typecheck
class LocalSession(Generic[_LocalCubes], BaseSession[_LocalCubes]):
    """Local session class."""

    def __init__(
        self,
        name: str,
        *,
        config: SessionConfig,
        detached_process: bool,
        distributed: bool,
    ):
        """Init."""
        super().__init__()
        self._name = name
        self._config = config

        self._create_subprocess_and_java_api(
            detached_process=detached_process, distributed=distributed
        )

        try:
            self._configure_session()
        except AtotiJavaException as ave:
            # Raise an exception if the session configuration fails
            raise AtotiException(
                f"{ave.java_traceback}\n"
                f"An error occurred while configuring the session.\n"
                f"The logs are available at {self.logs_path}"
            ) from None

        self._closed = False

    def _create_subprocess_and_java_api(
        self,
        *,
        detached_process: bool,
        distributed: bool,
    ):
        py4j_java_port: int

        if detached_process:
            py4j_java_port = _PY4J_DEFAULT_PORT
            self._server_subprocess = None
            logging.getLogger("atoti.process").warning(
                "detached_process: expecting a running server with Py4J listening on port %d",
                py4j_java_port,
            )
        else:
            self._server_subprocess = ServerSubprocess(config=self._config)
            py4j_java_port = self._server_subprocess.py4j_java_port

        self._java_api: JavaApi = JavaApi(
            py4j_java_port=py4j_java_port, distributed=distributed
        )

    @property
    def name(self) -> str:
        """Name of the session."""
        return self._name

    @property
    @abstractmethod
    def cubes(self) -> _LocalCubes:
        """Cubes of the session."""

    @property
    def closed(self) -> bool:
        """Return whether the session is closed or not."""
        return self._closed

    @property
    def port(self) -> int:
        """Port on which the session is exposed.

        Can be configured with :attr:`~atoti.config.session_config.SessionConfig.port`.
        """
        return self._java_api.get_session_port()

    @property
    def logs_path(self) -> Path:
        """Path to the session logs file."""
        if not self._server_subprocess:
            raise NotImplementedError(
                "The logs path is not available when using a query server process"
            )
        return self._server_subprocess.logs_path

    @property
    def security(self) -> Any:
        raise MissingPluginError("plus")

    def _configure_session(self):
        """Configure the session."""
        # Configure the plugins first
        for plugin in get_active_plugins().values():
            plugin.init_session(self)

        if self._config is not None:
            self._java_api.configure_session(self._config)

        self._java_api.start_application()

    def _set_client_side_encryption(self, client_side_encryption: ClientSideEncryption):
        deprecated(
            "Setting client side encryption through the session configuration is deprecated. Use read_*() and load_*()'s `client_side_encryption` parameter instead."
        )
        self._java_api._client_side_encryption = client_side_encryption

    def __exit__(  # pylint: disable=too-many-positional-parameters
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Exit this session's context manager.

        Close the session.

        """
        self.close()

    def _clear(self):
        """Clear this session and free all the associated resources."""
        self._java_api.clear_session()

    def close(self) -> None:
        """Close this session and free all the associated resources."""
        self._java_api.shutdown()
        if self._server_subprocess:
            self.wait()
        self._closed = True

    def wait(self) -> None:
        """Wait for the underlying server subprocess to terminate.

        This will prevent the Python process to exit.
        """
        if self._server_subprocess is None:
            raise ValueError("Server subprocess is not defined")
        self._server_subprocess.wait()

    def _generate_token(self) -> str:
        """Return a token that can be used to authenticate against the server."""
        return self._java_api.generate_jwt()

    def _open_transient_query_session(self) -> QuerySession:
        from .query.auth import Auth as QueryAuth
        from .query.session import QuerySession

        headers = self._generate_auth_headers()
        auth: Optional[QueryAuth] = (lambda _url: headers) if headers else None
        return QuerySession(f"http://localhost:{self.port}", auth=auth, name=self.name)

    @doc(_get_query_mdx_doc(is_query_session=False))
    def query_mdx(
        self, mdx: str, *, keep_totals: bool = False, timeout: int = 30
    ) -> QueryResult:
        get_level_data_types: GetLevelDataTypes = (
            lambda cube_name, levels_coordinates: self.cubes[
                cube_name
            ]._get_level_data_types(levels_coordinates)
        )

        return self._open_transient_query_session().query_mdx(
            mdx,
            get_level_data_types=get_level_data_types,
            keep_totals=keep_totals,
            timeout=timeout,
            session=self,
        )

    @doc(EXPLAIN_QUERY_DOC, corresponding_method="query_mdx")
    def explain_mdx_query(self, mdx: str, *, timeout: int = 30) -> QueryAnalysis:
        return self._java_api.analyse_mdx(mdx, timeout)

    def _generate_auth_headers(self) -> Dict[str, str]:
        """Generate the authentication headers to use for this session."""
        return {"Authorization": f"Jwt {self._java_api.generate_jwt()}"}

    def endpoint(
        self, route: str, *, method: Literal["POST", "GET", "PUT", "DELETE"] = "GET"
    ) -> Any:
        """Create a custom endpoint at ``/atoti/pyapi/{route}"``.

        This is useful to reuse atoti's built-in server instead of adding a `FastAPI <https://fastapi.tiangolo.com/>`__ or `Flask <https://flask.palletsprojects.com/>`__ server to the project.
        This way, when deploying the project in a container or a VM, only one port (the one of the atoti server) can be exposed instead of two.
        Since custom endpoints are exposed by atoti's server, they automatically inherit from the configured :attr:`atoti.config.session_config.SessionConfig.authentication` and :attr:`atoti.config.session_config.SessionConfig.https` parameters.

        The decorated function must take three parameters with types :class:`~atoti.pyapi.user.User`, :class:`~atoti.pyapi.http_request.HttpRequest`, and :class:`~atoti.session.Session` and return a response body as a Python data structure that can be converted to JSON.

        Args:
            route: The path suffix after ``/atoti/pyapi/``.
                For instance, if ``custom/search`` is passed, a request to ``/atoti/pyapi/custom/search?query=test#results`` will match.
                The route should not contain the query (``?``) or fragment (``#``).

                Path parameters can be configured by wrapping their name in curly braces in the route.
            method: The HTTP method the request must be using to trigger this endpoint.
                ``DELETE``, ``POST``, and ``PUT`` requests can have a body but it must be JSON.

        Example:
            .. doctest:: Session.endpoint
                :skipif: True

                >>> import requests
                >>> df = pd.DataFrame(
                ...     columns=["Year", "Month", "Day", "Quantity"],
                ...     data=[
                ...         (2019, 7, 1, 15),
                ...         (2019, 7, 2, 20),
                ...     ],
                ... )
                >>> table = session.read_pandas(df, table_name="Quantity")
                >>> table.head()
                Year  Month  Day  Quantity
                0  2019      7    1        15
                1  2019      7    2        20
                >>> endpoints_base_url = f"http://localhost:{session.port}/atoti/pyapi"
                >>> @session.endpoint("tables/{table_name}/size", method="GET")
                ... def get_table_size(request, user, session):
                ...     table_name = request.path_parameters["table_name"]
                ...     return len(session.tables[table_name])
                >>> requests.get(f"{endpoints_base_url}/tables/Quantity/size").json()
                2
                >>> @session.endpoint("tables/{table_name}/rows", method="POST")
                ... def append_rows_to_table(request, user, session):
                ...     rows = request.body
                ...     table_name = request.path_parameters["table_name"]
                ...     session.tables[table_name].append(*rows)
                >>> requests.post(
                ...     f"{endpoints_base_url}/tables/Quantity/rows",
                ...     json=[
                ...         {"Year": 2021, "Month": 5, "Day": 19, "Quantity": 50},
                ...         {"Year": 2021, "Month": 5, "Day": 20, "Quantity": 6},
                ...     ],
                ... ).status_code
                200
                >>> requests.get(f"{endpoints_base_url}/tables/Quantity/size").json()
                4
                >>> table.head()
                Year  Month  Day  Quantity
                0  2019      7    1        15
                1  2019      7    2        20
                2  2021      5   19        50
                3  2021      5   20         6

        """
        if route[0] == "/" or "?" in route or "#" in route:
            raise ValueError(
                f"Invalid route '{route}'. It should not start with '/' and not contain '?' or '#'."
            )

        def endpoint_decorator(func: CallbackEndpoint) -> Callable:
            self._java_api.create_endpoint(
                http_method=method,
                route=route,
                handler=EndpointHandler(func, self),
            )
            return func

        return endpoint_decorator

    def export_translations_template(self, path: PathLike) -> None:
        """Export a template containing all translatable values in the session's cubes.

        Args:
            path: The path at which to write the template.
        """
        self._java_api.export_i18n_template(path)

    def _create_flight_recording(self, path: PathLike, *, duration: timedelta) -> None:
        """Create a recording file using Java Flight Recorder (JFR)

        Args:
            path: The path (with a :guilabel:`.jfr` extension) at which the recording file should be written to.
            duration: The duration of the recording.

        """

        if not self._server_subprocess:
            raise RuntimeError("Cannot create flight recording for detached process.")

        command = [
            str(get_java_path(executable_name="jcmd")),
            str(self._server_subprocess._process.pid),
            "JFR.start",
            f"duration={int(duration.total_seconds())}s",
            f"filename={to_absolute_path(path)}",
        ]

        try:
            check_output(  # nosec
                command,
                stderr=STDOUT,
                text=True,
            )
        except CalledProcessError as error:
            raise RuntimeError(
                f"Failed to create flight recording:\n{error.output}"
            ) from error
