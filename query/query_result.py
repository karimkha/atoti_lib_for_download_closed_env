from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import pandas as pd
from typeguard import typeguard_ignore

from ._context import Context
from ._widget_conversion_details import WidgetConversionDetails

if TYPE_CHECKING:
    from pandas.io.formats.style import Styler


class QueryResult(pd.DataFrame):  # pylint: disable=abstract-method
    """pandas DataFrame corresponding to the result of a query.

    It is indexed by the queried levels.

    .. note::
        Unless mutated in place, the ``__repr__()``, ``_repr_html_()``, ``_repr_latex_()``, and ``_repr_mimebundle_()`` methods will use:

        * The caption of levels and members instead of their name.
        * The formatted value of measures instead of their value.
    """

    # See https://pandas.pydata.org/pandas-docs/stable/development/extending.html#define-original-properties
    _internal_names = pd.DataFrame._internal_names + [  # type: ignore
        "_atoti_context",
        "_atoti_formatted_values",
        "_atoti_get_styler",
        "_atoti_has_been_mutated",
        "_atoti_initial_dataframe",
        "_atoti_widget_conversion_details",
    ]
    _internal_names_set = set(_internal_names)

    @typeguard_ignore
    def __init__(
        self,
        # pandas does not expose the types of these arguments so we use Any instead.
        data: Any = None,
        index: Any = None,
        *,
        context: Optional[Context] = None,
        formatted_values: pd.DataFrame,
        get_styler: Callable[[], Styler],
    ):
        """Init the parent DataFrame and set extra internal attributes."""
        super().__init__(data, index)
        self._atoti_context = context
        self._atoti_formatted_values = formatted_values
        self._atoti_get_styler = get_styler
        self._atoti_has_been_mutated = False
        self._atoti_initial_dataframe = self.copy(deep=True)
        self._atoti_widget_conversion_details: Optional[WidgetConversionDetails] = None

    # The conversion to an atoti widget and the styling are based on the fact that this dataframe represents the original result of the MDX query.
    # If the dataframe was mutated, these features should be disabled to prevent them from being incorrect.
    def _has_been_mutated(self):
        if not self._atoti_has_been_mutated:
            if not self.equals(self._atoti_initial_dataframe):
                self._atoti_has_been_mutated = True

                logging.getLogger("atoti.query").warning(
                    "The query result has been mutated: captions, formatted values, and styling will not be shown."
                )

        return self._atoti_has_been_mutated

    @property
    def style(self) -> Styler:
        """Return a Styler object.

        If the query result has not been mutated, the returned object will follow the styling included in the CellSet from which the DataFrame was converted.
        """
        return super().style if self._has_been_mutated() else self._atoti_get_styler()

    def _get_dataframe_to_repr(self, *, has_been_mutated: bool) -> pd.DataFrame:
        return super() if has_been_mutated else self._atoti_formatted_values

    def _atoti_repr(self, *, has_been_mutated: bool) -> str:
        return self._get_dataframe_to_repr(has_been_mutated=has_been_mutated).__repr__()

    def __repr__(self) -> str:  # noqa: D105
        return self._atoti_repr(has_been_mutated=self._has_been_mutated())

    def _atoti_repr_html(self, *, has_been_mutated: bool) -> str:
        return self._get_dataframe_to_repr(
            has_been_mutated=has_been_mutated
        )._repr_html_()

    def _repr_html_(self) -> str:
        return self._atoti_repr_html(has_been_mutated=self._has_been_mutated())

    def _atoti_repr_latex(self, *, has_been_mutated: bool) -> str:
        return self._get_dataframe_to_repr(
            has_been_mutated=has_been_mutated
        )._repr_latex_()

    def _repr_latex_(self) -> str:
        return self._atoti_repr_latex(has_been_mutated=self._has_been_mutated())

    def _repr_mimebundle_(
        self, include: Any, exclude: Any  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        has_been_mutated = self._has_been_mutated()

        return {
            "text/html": self._atoti_repr_html(has_been_mutated=has_been_mutated),
            "text/plain": self._atoti_repr(has_been_mutated=has_been_mutated),
        }
