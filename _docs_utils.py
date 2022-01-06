from functools import wraps
from textwrap import dedent
from typing import Any, Callable, List, Union, cast

from ._type_utils import F


# Taken from Pandas:
# https://github.com/pandas-dev/pandas/blame/8aa707298428801199280b2b994632080591700a/pandas/util/_decorators.py#L332
def doc(*args: Union[str, Callable[..., Any]], **kwargs: str) -> Callable[[F], F]:
    """Take docstring templates, concatenate them and perform string substitution."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Callable[..., Any]:
            return func(*args, **kwargs)

        # Collecting docstring and docstring templates
        docstring_components: List[Union[str, Callable[..., Any]]] = []
        if func.__doc__:
            docstring_components.append(dedent(func.__doc__))

        for arg in cast(Any, args):
            if hasattr(arg, "_docstring_components"):
                docstring_components.extend(
                    cast(
                        Any,
                        arg,
                    )._docstring_components
                )
            elif isinstance(arg, str) or arg.__doc__:
                docstring_components.append(arg)

        # Formatting templates and concatenating docstring
        wrapper.__doc__ = "".join(
            [
                arg.format(**kwargs)
                if isinstance(arg, str)
                else dedent(arg.__doc__ or "")
                for arg in docstring_components
            ]
        )

        wrapper._docstring_components = docstring_components  # type: ignore

        return cast(F, wrapper)

    return decorator


def get_query_args_doc(*, is_query_session: bool) -> str:
    lines = (
        [
            'session = tt.open_query_session(f"http://localhost:{session.port}")',
            "cube = session.cubes[cube.name]",
        ]
        if is_query_session
        else []
    ) + ["h, l, m = cube.hierarchies, cube.levels, cube.measures"]
    example_lines = "\n                        ".join([f">>> {line}" for line in lines])

    return f"""Args:
            measures: The measures to query.
            condition: The filtering condition.
                Only conditions on level equality with a string are supported.

                Examples:

                    .. doctest:: query

                        >>> df = pd.DataFrame(
                        ...     columns=["Continent", "Country", "Currency", "Price"],
                        ...     data=[
                        ...         ("Europe", "France", "EUR", 200.0),
                        ...         ("Europe", "Germany", "EUR", 150.0),
                        ...         ("Europe", "United Kingdom", "GBP", 120.0),
                        ...         ("America", "United states", "USD", 240.0),
                        ...         ("America", "Mexico", "MXN", 270.0),
                        ...     ],
                        ... )
                        >>> table = session.read_pandas(
                        ...     df,
                        ...     keys=["Continent", "Country", "Currency"],
                        ...     table_name="Prices",
                        ... )
                        >>> cube = session.create_cube(table)
                        >>> del cube.hierarchies["Continent"]
                        >>> del cube.hierarchies["Country"]
                        >>> cube.hierarchies["Geography"] = [
                        ...     table["Continent"],
                        ...     table["Country"],
                        ... ]
                        {example_lines}

                        >>> cube.query(
                        ...     m["Price.SUM"],
                        ...     levels=[l["Country"]],
                        ...     condition=l["Continent"] == "Europe",
                        ... )
                                                 Price.SUM
                        Continent Country
                        Europe    France            200.00
                                  Germany           150.00
                                  United Kingdom    120.00


                        >>> cube.query(
                        ...     m["Price.SUM"],
                        ...     levels=[l["Country"], l["Currency"]],
                        ...     condition=(
                        ...         (l["Continent"] == "Europe")
                        ...         & (l["Currency"] == "EUR")
                        ...     ),
                        ... )
                                                   Price.SUM
                        Continent Country Currency
                        Europe    France  EUR         200.00
                                  Germany EUR         150.00

                        >>> cube.query(
                        ...     m["Price.SUM"],
                        ...     levels=[l["Country"]],
                        ...     condition=h["Geography"].isin(
                        ...         ("America",), ("Europe", "Germany")
                        ...     ),
                        ... )
                                                Price.SUM
                        Continent Country
                        America   Mexico           270.00
                                  United states    240.00
                        Europe    Germany          150.00

            include_totals: Whether the returned DataFrame should include the grand total and subtotals.
                Totals can be useful but they make the DataFrame harder to work with since its index will have some empty values.

                Example:

                    .. doctest:: query

                            >>> cube.query(
                            ...     m["Price.SUM"],
                            ...     levels=[l["Country"], l["Currency"]],
                            ...     include_totals=True,
                            ... )
                                                              Price.SUM
                            Continent Country        Currency
                            Total                                980.00
                            America                              510.00
                                      Mexico                     270.00
                                                     MXN         270.00
                                      United states              240.00
                                                     USD         240.00
                            Europe                               470.00
                                      France                     200.00
                                                     EUR         200.00
                                      Germany                    150.00
                                                     EUR         150.00
                                      United Kingdom             120.00
                                                     GBP         120.00

            levels: The levels to split on.
                If ``None``, the value of the measures at the top of the cube is returned.
            scenario: The scenario to query.
            timeout: The query timeout in seconds.
"""


EXPLAIN_QUERY_DOC = """Run the query but return an explanation of how the query was executed instead of its result.

        See also:
            :meth:`{corresponding_method}` for the roles of the parameters.

        Returns:
            An explanation containing a summary, global timings, and the query plan with all the retrievals.
        """

QUERY_DOC = """Query the cube to retrieve the value of the passed measures on the given levels.

        In JupyterLab with the :mod:`atoti-jupyterlab <atoti_jupyterlab>` plugin installed, query results can be converted to interactive widgets with the :guilabel:`Convert to Widget Below` action available in the command palette or by right clicking on the representation of the returned Dataframe.

        {args}
"""

CLIENT_SIDE_ENCRYPTION_DOC = {
    "client_side_encryption": """client_side_encryption: The client side encryption configuration to use when loading data."""
}

CSV_KWARGS = {
    "array_separator": """array_separator: The character separating array elements.
                Setting it to a non-``None`` value will parse all the columns containing this separator as arrays.""",
    "encoding": """encoding: The encoding to use to read the CSV.""",
    "path": """path: The path to the CSV file to load.

                ``.gz``, ``.tar.gz`` and ``.zip`` files containing compressed CSV(s) are also supported.

                The path can also be a glob pattern (e.g. ``path/to/directory/**.*.csv``).""",
    "process_quotes": """process_quotes: Whether double quotes should be processed to follow the official CSV specification:

                * ``True``:

                    * Each field may or may not be enclosed in double quotes (however some programs, such as Microsoft Excel, do not use double quotes at all).
                      If fields are not enclosed with double quotes, then double quotes may not appear inside the fields.
                    * A double quote appearing inside a field must be escaped by preceding it with another double quote.
                    * Fields containing line breaks, double quotes, and commas should be enclosed in double-quotes.
                * ``False``: all double-quotes within a field will be treated as any regular character, following Excel's behavior.
                  In this mode, it is expected that fields are not enclosed in double quotes.
                  It is also not possible to have a line break inside a field.
                * ``None``: The behavior will be inferred from the first lines of the CSV file.""",
    "date_patterns": """date_patterns: A column name to `date pattern <https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/time/format/DateTimeFormatter.html>`__ mapping that can be used when the built-in date parsers fail to recognize the formatted dates in the passed files.""",
    "separator": """separator: The character separating the values of each line.
                the separator will be detected automatically.""",
}

HEAD_DOC = """Return *n* rows of the {what} as a pandas DataFrame."""

LEVEL_ISIN_DOC = """Return a condition to check that the level is on one of the given members.

        ``level.isin(a, b)`` is equivalent to ``(level == a) OR (level == b)``.

        Args:
            members: One or more members on which the level should be.

        Example:
            .. doctest:: Level.isin

                >>> df = pd.DataFrame(
                ...     columns=["City", "Price"],
                ...     data=[
                ...         ("Berlin", 150.0),
                ...         ("London", 240.0),
                ...         ("New York", 270.0),
                ...         ("Paris", 200.0),
                ...     ],
                ... )
                >>> table = session.read_pandas(
                ...     df, keys=["City"], table_name="isin example"
                ... )
                >>> cube = session.create_cube(table)
                >>> l, m = cube.levels, cube.measures
                >>> m["Price.SUM in London and Paris"] = tt.filter(
                ...     m["Price.SUM"], l["City"].isin("London", "Paris")
                ... )
                >>> cube.query(
                ...     m["Price.SUM"],
                ...     m["Price.SUM in London and Paris"],
                ...     levels=[l["City"]],
                ... )
                         Price.SUM Price.SUM in London and Paris
                City
                Berlin      150.00
                London      240.00                        240.00
                New York    270.00
                Paris       200.00                        200.00

            .. doctest:: Level.isin
                :hide:

                Clear the session to isolate the multiple methods sharing this docstring.
                >>> session._clear()

"""

HIERARCHY_ISIN_DOC = """Return a condition to check that the hierarchy is on one of the given members.

        Considering ``hierarchy_1`` containing ``level_1`` and ``level_2``, ``hierarchy_1.isin((a,), (b, x))`` is equivalent to ``(level_1 == a) OR ((level_1 == b) AND (level_2 == x))``.

        Args:
            members: One or more members expressed as tuples on which the hierarchy should be.
                Each element in a tuple corresponds to a level of the hierarchy, from the shallowest to the deepest.

        Example:
            .. doctest:: Hierarchy.isin

                >>> df = pd.DataFrame(
                ...     columns=["Country", "City", "Price"],
                ...     data=[
                ...         ("Germany", "Berlin", 150.0),
                ...         ("Germany", "Hamburg", 120.0),
                ...         ("United Kingdom", "London", 240.0),
                ...         ("United States", "New York", 270.0),
                ...         ("France", "Paris", 200.0),
                ...     ],
                ... )
                >>> table = session.read_pandas(
                ...     df, keys=["Country", "City"], table_name="isin example"
                ... )
                >>> cube = session.create_cube(table)
                >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
                >>> h["Geography"] = [l["Country"], l["City"]]
                >>> m["Price.SUM in Germany and Paris"] = tt.filter(
                ...     m["Price.SUM"],
                ...     h["Geography"].isin(("Germany",), ("France", "Paris")),
                ... )
                >>> cube.query(
                ...     m["Price.SUM"],
                ...     m["Price.SUM in Germany and Paris"],
                ...     levels=[l["Geography", "City"]],
                ... )
                                        Price.SUM Price.SUM in Germany and Paris
                Country        City
                France         Paris       200.00                         200.00
                Germany        Berlin      150.00                         150.00
                               Hamburg     120.00                         120.00
                United Kingdom London      240.00
                United States  New York    270.00

            .. doctest:: Hierarchy.isin
                :hide:

                Clear the session to isolate the multiple methods sharing this docstring.
                >>> session._clear()
"""

PARQUET_KWARGS = {
    "path": """path: The path to the Parquet file.
                If a path pointing to a directory is provided, all of the files with the ``.parquet`` extension in the directory will be loaded into the same table and, as such, they are all expected to share the same schema.
                The path can also be a glob pattern (e.g. ``path/to/directory/**.*.parquet``)."""
}

QUANTILE_DOC = """Return a measure equal to the requested quantile {what}.

    Here is how to obtain the same behavior as `these standard quantile calculation methods <https://en.wikipedia.org/wiki/Quantile#Estimating_quantiles_from_a_sample>`__:

    * R-1: ``mode="centered"`` and ``interpolation="lower"``
    * R-2: ``mode="centered"`` and ``interpolation="midpoint"``
    * R-3: ``mode="simple"`` and ``interpolation="nearest"``
    * R-4: ``mode="simple"`` and ``interpolation="linear"``
    * R-5: ``mode="centered"`` and ``interpolation="linear"``
    * R-6 (similar to Excel's ``PERCENTILE.EXC``): ``mode="exc"`` and ``interpolation="linear"``
    * R-7 (similar to Excel's ``PERCENTILE.INC``): ``mode="inc"`` and ``interpolation="linear"``
    * R-8 and R-9 are not supported

    The formulae given for the calculation of the quantile index assume a 1-based indexing system.

    Args:
        measure: The measure to get the quantile of.
        q: The quantile to take.
            Must be between ``0`` and ``1``.
            For instance, ``0.95`` is the 95th percentile and ``0.5`` is the median.
        mode: The method used to calculate the index of the quantile.
            Available options are, when searching for the *q* quantile of a vector ``X``:

            * ``simple``: ``len(X) * q``
            * ``centered``: ``len(X) * q + 0.5``
            * ``exc``: ``(len(X) + 1) * q``
            * ``inc``: ``(len(X) - 1) * q + 1``

        interpolation: If the quantile index is not an integer, the interpolation decides what value is returned.
            The different options are, considering a quantile index ``k`` with ``i < k < j`` for a sorted vector ``X``:

            - ``linear``: ``v = X[i] + (X[j] - X[i]) * (k - i)``
            - ``lowest``: ``v = X[i]``
            - ``highest``: ``v = X[j]``
            - ``nearest``: ``v = X[i]`` or ``v = X[j]`` depending on which of ``i`` or ``j`` is closest to ``k``
            - ``midpoint``: ``v = (X[i] + X[j]) / 2``
"""

QUANTILE_INDEX_DOC = """Return a measure equal to the index of requested quantile {what}.

    Args:
        measure: The measure to get the quantile of.
        q: The quantile to take.
            Must be between ``0`` and ``1``.
            For instance, ``0.95`` is the 95th percentile and ``0.5`` is the median.
        mode: The method used to calculate the index of the quantile.
            Available options are, when searching for the *q* quantile of a vector ``X``:

            * ``simple``: ``len(X) * q``
            * ``centered``: ``len(X) * q + 0.5``
            * ``exc``: ``(len(X) + 1) * q``
            * ``inc``: ``(len(X) - 1) * q + 1``

        interpolation: If the quantile index is not an integer, the interpolation decides what value is returned.
            The different options are, considering a quantile index ``k`` with ``i < k < j`` for the original vector ``X``
            and the sorted vector ``Y``:

            - ``lowest``: the index in ``X`` of ``Y[i]``
            - ``highest``: the index in ``X`` of ``Y[j]``
            - ``nearest``: the index in ``X`` of ``Y[i]`` or ``Y[j]`` depending on which of ``i`` or ``j`` is closest to ``k``
"""

STD_DOC_KWARGS = {
    "op": "standard deviation",
    "population_excel": "STDEV.P",
    "population_formula": "\\sqrt{\\frac{\\sum_{i=0}^{n}(X_i - m)^{2}}{n}}",
    "sample_excel": "STDEV.S",
    "sample_formula": "\\sqrt{\\frac{\\sum_{i=0}^{n} (X_i - m)^{2}}{n - 1}}",
}
VAR_DOC_KWARGS = {
    "op": "variance",
    "population_excel": "VAR.P",
    "population_formula": "\\frac{\\sum_{i=0}^{n}(X_i - m)^{2}}{n}",
    "sample_excel": "VAR.S",
    "sample_formula": "\\frac{\\sum_{i=0}^{n} (X_i - m)^{2}}{n - 1}",
}

STD_AND_VAR_DOC = """Return a measure equal to the {op} {what}.

    Args:
        measure: The measure to get the {op} of.
        mode: One of the supported modes:

            * The ``sample`` {op}, similar to Excel's ``{sample_excel}``, is :math:`{sample_formula}` where ``m`` is the sample mean and ``n`` the size of the sample.
              Use this mode if the data represents a sample of the population.
            * The ``population`` {op}, similar to Excel's ``{population_excel}`` is :math:`{population_formula}` where ``m`` is the mean of the ``Xi`` elements and ``n`` the size of the population.
              Use this mode if the data represents the entire population.
"""

TABLE_APPEND_DOC = """Add one or multiple rows to the {what}.

        If a row with the same keys already exist in the {what}, it will be overridden by the passed one.

        Args:
            rows: The rows to add.
                Rows can either be:

                * Tuples of values in the correct order.
                * Column name to value mappings.

                All rows must share the shame shape.
"""

TABLE_CREATION_KWARGS = {
    "keys": """keys: The columns that will become keys of the table.""",
    "partitioning": """partitioning : The description of how the data will be split across partitions of the table.

                Only key columns can be used in the partitioning description.
                Joined tables can only use a sub-partitioning of the table referencing them.

                Example:

                    ``hash4(country)`` splits the data across 4 partitions based on the :guilabel:`country` column's hash value.""",
    "table_name": """table_name: The name of the table to create.""",
    "hierarchized_columns": """hierarchized_columns: The list of columns which will automatically be converted into hierarchies no matter which creation mode is used for the cube.

                The different behaviors based on the passed value are:

                    * ``None``: all non-numeric columns are converted into hierarchies, depending on the cube's creation mode.
                    * Empty collection: no columns are converted into hierarchies.
                    * Non-empty collection: only the columns in the collection will be converted into hierarchies.

                For partial joins, the un-mapped key columns of the target table are always converted into hierarchies, regardless of the value of this parameter.
        """,
}

TABLE_IADD_DOC = """Add a single row to the {what}."""
