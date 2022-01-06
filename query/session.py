import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Union
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .._base._base_session import BaseSession
from .._docs_utils import doc
from ._cellset import Cellset, GetLevelDataTypes, cellset_to_query_result
from ._context import Context
from ._discovery import Discovery
from ._discovery_utils import create_cubes_from_discovery
from ._widget_conversion_details import WidgetConversionDetails
from .auth import Auth
from .cubes import QueryCubes
from .query_result import QueryResult

SUPPORTED_VERSIONS = ["5", "5.Z1", "4", "6zz1"]


def _get_query_mdx_doc(*, is_query_session: bool) -> str:
    return f"""Execute an MDX query and return its result as a pandas DataFrame.

        Args:
            mdx: The MDX ``SELECT`` query to execute.
                Regardless of the axes on which levels and measures appear in the MDX, the returned DataFrame will have all levels on rows and measures on columns.
            keep_totals: Whether the resulting DataFrame should contain, if they are present in the query result, the grand total and subtotals.
                Totals can be useful but they make the DataFrame harder to work with since its index will have some empty values.
            timeout: The query timeout in seconds.

        Example:

            .. doctest:: query_mdx

                >>> from datetime import date
                >>> df = pd.DataFrame(
                ...     columns=["Country", "Date", "Price"],
                ...     data=[
                ...         ("China", date(2020, 3, 3), 410.0),
                ...         ("China", date(2020, 4, 4), 350.0),
                ...         ("France", date(2020, 1, 1), 480.0),
                ...         ("France", date(2020, 2, 2), 500.0),
                ...         ("France", date(2020, 3, 3), 400.0),
                ...         ("France", date(2020, 4, 4), 420.0),
                ...         ("India", date(2020, 1, 1), 360.0),
                ...         ("India", date(2020, 2, 2), 400.0),
                ...         ("UK", date(2020, 2, 2), 960.0),
                ...     ],
                ... )
                >>> table = session.read_pandas(
                ...     df, keys=["Country", "Date"], table_name="Prices"
                ... )
                >>> _ = session.create_cube(table)
                {'>>> session = tt.open_query_session("http://localhost:" + str(session.port))' if is_query_session else ""}

            This MDX:

            .. doctest:: query_mdx

                >>> mdx = (
                ...     "SELECT"
                ...     "  NON EMPTY Hierarchize("
                ...     "    DrilldownLevel("
                ...     "      [Prices].[Country].[ALL].[AllMember]"
                ...     "    )"
                ...     "  ) ON ROWS,"
                ...     "  NON EMPTY Crossjoin("
                ...     "    [Measures].[Price.SUM],"
                ...     "    Hierarchize("
                ...     "      DrilldownLevel("
                ...     "        [Prices].[Date].[ALL].[AllMember]"
                ...     "      )"
                ...     "    )"
                ...     "  ) ON COLUMNS"
                ...     "  FROM [Prices]"
                ... )

            would display this pivot table:

            +---------+--------------------------------------------------------------+
            | Country | Price.sum                                                    |
            |         +----------+------------+------------+------------+------------+
            |         | Total    | 2020-01-01 | 2020-02-02 | 2020-03-03 | 2020-04-04 |
            +---------+----------+------------+------------+------------+------------+
            | Total   | 2,280.00 | 840.00     | 1,860.00   | 810.00     | 770.00     |
            +---------+----------+------------+------------+------------+------------+
            | China   | 760.00   |            |            | 410.00     | 350.00     |
            +---------+----------+------------+------------+------------+------------+
            | France  | 1,800.00 | 480.00     | 500.00     | 400.00     | 420.00     |
            +---------+----------+------------+------------+------------+------------+
            | India   | 760.00   | 360.00     | 400.00     |            |            |
            +---------+----------+------------+------------+------------+------------+
            | UK      | 960.00   |            | 960.00     |            |            |
            +---------+----------+------------+------------+------------+------------+

            but will return this DataFrame:

            .. doctest:: query_mdx

                >>> session.query_mdx(mdx).sort_index()
                                    Price.SUM
                Date       Country
                2020-01-01 France       480.0
                           India        360.0
                2020-02-02 France       500.0
                           India        400.0
                           UK           960.0
                2020-03-03 China        410.0
                           France       400.0
                2020-04-04 China        350.0
                           France       420.0

"""


@dataclass(frozen=True)
class _QuerySessionPrivateParameters:
    session: Optional[BaseSession] = None
    get_level_data_types: Optional[GetLevelDataTypes] = None
    context: Context = field(default_factory=dict)


class QuerySession(BaseSession[QueryCubes]):
    """Used to query an existing session.

    Query sessions are immutable: the structure of their underlying cubes is not expected to change.
    """

    def __init__(
        self, url: str, *, auth: Optional[Auth] = None, name: Optional[str] = None
    ):
        """Init.

        Args:
            url: The server base URL.
            auth: The authentication to use.
            name: The name to give to the session.
        """
        from .._plugins import get_active_plugins

        super().__init__()
        self._url = url
        self._name = name or url
        self._auth = auth or (lambda url: None)
        self._version = self._fetch_version()
        self._discovery = self._fetch_discovery()
        self._cubes = create_cubes_from_discovery(self._discovery, self)
        plugins = get_active_plugins().values()
        for plugin in plugins:
            plugin.init_query_session(self)

    @property
    def cubes(self) -> QueryCubes:
        """Cubes of the session."""
        return self._cubes

    @property
    def name(self) -> str:
        """Name of the session."""
        return self._name

    @property
    def url(self) -> str:
        """URL of the session."""
        return self._url

    def _generate_auth_headers(self) -> Mapping[str, str]:
        """Generate the authentication headers to use for this session."""
        return self._auth(self.url) or {}

    def _execute_json_request(self, url: str, *, body: Optional[Any] = None) -> Any:
        headers = {"Content-Type": "application/json"}
        headers.update(self._auth(url) or {})
        data = json.dumps(body).encode("utf8") if body else None
        # The user can send any URL, wrapping it in a request object makes it a bit safer
        request = Request(url, data=data, headers=headers)
        try:
            with urlopen(request) as response:  # nosec
                return json.load(response)
        except HTTPError as error:
            error_json = error.read()
            error_data = json.loads(error_json)
            raise RuntimeError("Request failed", error_data) from error

    def _fetch_versions(self) -> Any:
        url = urljoin(f"{self.url}/", "versions/rest")
        return self._execute_json_request(url)

    def _fetch_version(self) -> str:
        response = self._fetch_versions()
        exposed_versions = [
            version["id"] for version in response["apis"]["pivot"]["versions"]
        ]
        try:
            return next(
                version for version in SUPPORTED_VERSIONS if version in exposed_versions
            )
        except Exception:
            raise RuntimeError(
                f"Exposed versions: {exposed_versions}"
                f" don't match supported ones: {SUPPORTED_VERSIONS}"
            ) from None

    def _fetch_discovery(self) -> Discovery:
        url = urljoin(f"{self.url}/", f"pivot/rest/v{self._version}/cube/discovery")
        response = self._execute_json_request(url)
        return response["data"]

    def _query_mdx_to_cellset(self, mdx: str, *, context: Context) -> Cellset:
        url = urljoin(f"{self.url}/", f"pivot/rest/v{self._version}/cube/query/mdx")
        body: Mapping[str, Union[str, Context]] = {"context": context, "mdx": mdx}
        response = self._execute_json_request(url, body=body)
        return response["data"]

    @doc(_get_query_mdx_doc(is_query_session=True))
    def query_mdx(
        self,
        mdx: str,
        *,
        keep_totals: bool = False,
        timeout: int = 30,
        **kwargs: Any,
    ) -> QueryResult:
        private_parameters = _QuerySessionPrivateParameters(**kwargs)
        context = private_parameters.context
        if timeout is not None:
            context = {**context, "queriesTimeLimit": timeout}
        cellset = self._query_mdx_to_cellset(mdx, context=context)
        query_result = cellset_to_query_result(
            cellset,
            context=context,
            discovery=self._discovery,
            get_level_data_types=private_parameters.get_level_data_types,
            keep_totals=keep_totals,
        )
        # Let local sessions pass their reference to have the correct name and widget creation code.
        session = (
            private_parameters.session
            if private_parameters.session is not None
            else self
        )
        query_result._atoti_widget_conversion_details = WidgetConversionDetails(
            mdx=mdx,
            session_id=session._id,
            widget_creation_code=session._get_widget_creation_code(),
        )
        return query_result
