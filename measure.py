from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Sequence, Tuple

from typeguard import typechecked, typeguard_ignore

from ._base._base_measure import BaseMeasure
from ._bitwise_operators_only import IdentityElement
from ._deprecation import deprecated
from .measure_description import MeasureDescription
from .type import DataType

if TYPE_CHECKING:
    from ._java_api import JavaApi
    from .cube import Cube


@typeguard_ignore
@dataclass(eq=False)
class Measure(MeasureDescription, BaseMeasure):
    """A measure is a mostly-numeric data value, computed on demand for aggregation purposes.

    Measures can be compared to other objects, such as a literal value, a :class:`~atoti.level.Level`, or another measure.
    The returned measure represents the outcome of the comparison and this measure can be used as a condition.
    If the measure's value is ``None`` when evaluating a condition, the returned value will be ``False``.

    Example:
        >>> df = pd.DataFrame(
        ...     columns=["Id", "Value", "Threshold"],
        ...     data=[
        ...         (0, 1.0, 5.0),
        ...         (1, 2.0, None),
        ...         (2, 3.0, 3.0),
        ...         (3, 4.0, None),
        ...         (4, 5.0, 1.0),
        ...     ],
        ... )
        >>> table = session.read_pandas(df, keys=["Id"], table_name="Measure example")
        >>> cube = session.create_cube(table)
        >>> l, m = cube.levels, cube.measures
        >>> m["Condition"] = m["Value.SUM"] > m["Threshold.SUM"]
        >>> cube.query(m["Condition"], levels=[l["Id"]])
           Condition
        Id
        0      False
        1      False
        2      False
        3      False
        4       True

    """

    _data_type: DataType
    _cube: Cube = field(repr=False)
    _java_api: JavaApi = field(repr=False)
    _folder: Optional[str] = None
    _formatter: Optional[str] = None
    _visible: bool = True
    _description: Optional[str] = None

    @property
    def data_type(self) -> DataType:
        """Type of the measure members."""
        return self._data_type

    @property
    def folder(self) -> Optional[str]:
        """Folder of the measure.

        Folders can be used to group measures in the :guilabel:`Data model` UI component.

        Example:
            >>> df = pd.DataFrame(
            ...     columns=["Product", "Price"],
            ...     data=[
            ...         ("phone", 600.0),
            ...         ("headset", 80.0),
            ...         ("watch", 250.0),
            ...     ],
            ... )
            >>> table = session.read_pandas(
            ...     df, keys=["Product"], table_name="Folder example"
            ... )
            >>> cube = session.create_cube(table)
            >>> m = cube.measures
            >>> print(m["Price.SUM"].folder)
            None
            >>> m["Price.SUM"].folder = "Prices"
            >>> m["Price.SUM"].folder
            'Prices'
            >>> del m["Price.SUM"].folder
            >>> print(m["Price.SUM"].folder)
            None

        """
        return self._folder

    @folder.setter
    @typechecked
    def folder(self, value: Optional[str]) -> None:
        if value is None:
            deprecated(
                "Setting the folder to `None` is deprecated. Delete it instead with `del`."
            )
            del self.folder
            return

        self._set_folder(value)

    @folder.deleter
    def folder(self) -> None:
        self._set_folder(None)

    def _set_folder(self, value: Optional[str]) -> None:
        self._folder = value
        self._java_api.set_measure_folder(
            cube_name=self._cube.name, measure=self, folder=value
        )
        self._java_api.publish_measures(self._cube.name)

    @property
    def formatter(self) -> Optional[str]:
        """Formatter of the measure.

        Note:
            The formatter only impacts how the measure is displayed, derived measures will still be computed from unformatted value.
            To round a measure, use :func:`atoti.math.round` instead.

        Example:
            >>> df = pd.DataFrame(
            ...     columns=["Product", "Price", "Quantity"],
            ...     data=[
            ...         ("phone", 559.99, 2),
            ...         ("headset", 79.99, 4),
            ...         ("watch", 249.99, 3),
            ...     ],
            ... )
            >>> table = session.read_pandas(
            ...     df, keys=["Product"], table_name="Formatter example"
            ... )
            >>> cube = session.create_cube(table)
            >>> h, l, m = cube.hierarchies, cube.levels, cube.measures
            >>> m["contributors.COUNT"].formatter
            'INT[#,###]'
            >>> m["contributors.COUNT"].formatter = "INT[count: #,###]"
            ...
            >>> m["contributors.COUNT"].formatter
            'INT[count: #,###]'
            >>> m["Price.SUM"].formatter
            'DOUBLE[#,###.00]'
            >>> m["Price.SUM"].formatter = "DOUBLE[$#,##0.00]"  # Add $ symbol
            >>> m["Ratio of sales"] = m["Price.SUM"] / tt.total(
            ...     m["Price.SUM"], h["Product"]
            ... )
            >>> m["Ratio of sales"].formatter
            'DOUBLE[#,###.00]'
            >>> m["Ratio of sales"].formatter = "DOUBLE[0.00%]"  # Percentage
            >>> m["Turnover in dollars"] = tt.agg.sum(
            ...     table["Price"] * table["Quantity"]
            ... )
            >>> m["Turnover in dollars"].formatter
            'DOUBLE[#,###.00]'
            >>> m["Turnover in dollars"].formatter = "DOUBLE[#,###]"  # Without decimals
            >>> cube.query(
            ...     m["contributors.COUNT"],
            ...     m["Price.SUM"],
            ...     m["Ratio of sales"],
            ...     m["Turnover in dollars"],
            ...     levels=[l["Product"]],
            ... )
                    contributors.COUNT Price.SUM Ratio of sales Turnover in dollars
            Product
            headset           count: 1    $79.99          8.99%                 320
            phone             count: 1   $559.99         62.92%               1,120
            watch             count: 1   $249.99         28.09%                 750

        The spec for the pattern between the ``DATE`` or ``DOUBLE``'s brackets is the one from `Microsoft Analysis Services <https://docs.microsoft.com/en-us/analysis-services/multidimensional-models/mdx/mdx-cell-properties-format-string-contents?view=asallproducts-allversions>`__.

        There is an extra formatter for array measures: ``ARRAY['|';1:3]`` where ``|`` is the separator used to join the elements of the ``1:3`` slice.
        """
        return self._formatter

    @formatter.setter
    @typechecked
    def formatter(self, value: Optional[str]) -> None:
        if value is None:
            # https://github.com/activeviam/atoti/issues/2690 needs to be fixed before this can be dropped.
            deprecated(
                "Setting the formatter to `None` is deprecated. Measures should always have a formatter."
            )

        self._formatter = value
        self._java_api.set_measure_formatter(
            cube_name=self._cube.name, measure=self, formatter=value
        )
        self._java_api.publish_measures(self._cube.name)

    @property
    def visible(self) -> bool:
        """Whether the measure is visible in notebooks and in the UI or not.

        Example:
            >>> df = pd.DataFrame(
            ...     columns=["Product", "Price"],
            ...     data=[
            ...         ("phone", 560),
            ...         ("headset", 80),
            ...         ("watch", 250),
            ...     ],
            ... )
            >>> table = session.read_pandas(
            ...     df, keys=["Product"], table_name="Visible example"
            ... )
            >>> cube = session.create_cube(table)
            >>> m = cube.measures
            >>> m["Price.SUM"].visible
            True
            >>> m["Price.SUM"].visible = False
            >>> m["Price.SUM"].visible
            False
            >>> m["contributors.COUNT"].visible
            True
            >>> m["contributors.COUNT"].visible = False
            >>> m["contributors.COUNT"].visible
            False
        """
        return self._visible

    @visible.setter
    @typechecked
    def visible(self, value: bool) -> None:
        self._visible = value
        self._java_api.set_visible(
            cube_name=self._cube.name, measure=self, visible=value
        )
        self._java_api.publish_measures(self._cube.name)

    # Not really useful until https://support.activeviam.com/jira/browse/UI-6634 is fixed.
    @property
    def description(self) -> Optional[str]:
        """Description of the measure.

        Example:
            >>> df = pd.DataFrame(
            ...     columns=["Product", "Price"],
            ...     data=[
            ...         ("phone", 560),
            ...         ("headset", 80),
            ...         ("watch", 250),
            ...     ],
            ... )
            >>> table = session.read_pandas(
            ...     df, keys=["Product"], table_name="Description example"
            ... )
            >>> cube = session.create_cube(table)
            >>> m = cube.measures
            >>> print(m["Price.SUM"].description)
            None
            >>> m["Price.SUM"].description = "The sum of the price"
            >>> m["Price.SUM"].description
            'The sum of the price'
            >>> del m["Price.SUM"].description
            >>> print(m["Price.SUM"].description)
            None

        """
        return self._description

    @description.setter
    @typechecked
    def description(self, value: Optional[str]) -> None:
        if value is None:
            deprecated(
                "Setting the description to `None` is deprecated. Delete it instead with `del`."
            )
            del self.description
            return

        self._set_description(value)

    @description.deleter
    @typechecked
    def description(self) -> None:
        self._set_description(None)

    def _set_description(self, value: Optional[str]) -> None:
        self._description = value
        self._java_api.set_measure_description(
            cube_name=self._cube.name, measure=self, description=value
        )
        self._java_api.publish_measures(self._cube.name)

    @property
    def _required_levels(self) -> Sequence[str]:
        """Levels required by this measure."""
        return self._java_api.get_required_levels(self)

    def _do_distil(  # pylint: disable=no-self-use
        self, *, java_api: JavaApi, cube: Cube, measure_name: Optional[str] = None
    ) -> str:
        raise ValueError("Cannot create a measure that already exists in the cube.")

    def _identity(self) -> Tuple[IdentityElement, ...]:
        return (self._name,)
