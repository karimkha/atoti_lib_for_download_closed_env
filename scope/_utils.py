from abc import abstractmethod
from dataclasses import dataclass
from typing import Collection, Optional, Tuple

from atoti._measures.generic_measure import GenericMeasure
from atoti.hierarchy import Hierarchy
from atoti.level import Level
from atoti.measure_description import MeasureDescription

from .scope import Scope


@dataclass(frozen=True)
class Window(Scope):
    """Window-like structure used in the computation of cumulative aggregations."""

    @abstractmethod
    def _create_aggregated_measure(
        self, measure: MeasureDescription, agg_fun: str
    ) -> MeasureDescription:
        """Create the appropriate aggregated measure for this window.

        Args:
            measure: The underlying measure to aggregate
            agg_fun: The aggregation function to use.
        """


@dataclass(frozen=True)
class CumulativeWindow(Window):
    """Implementation of a Window for member-based cumulative aggregations.

    It contains a level, its range of members which is (-inf, 0) by default, and a partitioning consisting of levels in that hierarchy.
    """

    _level: Level
    _dense: bool
    _window: Optional[range]
    _partitioning: Optional[Level] = None

    def _create_aggregated_measure(
        self, measure: MeasureDescription, agg_fun: str
    ) -> MeasureDescription:
        return GenericMeasure(
            "WINDOW_AGG",
            measure,
            self._level,
            self._partitioning,
            agg_fun,
            (self._window.start, self._window.stop) if self._window else None,
            self._dense,
        )


@dataclass(frozen=True)
class CumulativeTimeWindow(Window):
    """Implementation of a Window for time-based cumulative aggregations.

    It contains a level, its time range defined by two strings, and a partitioning consisting of levels in that hierarchy.
    """

    _level: Level
    _window: Tuple[Optional[str], Optional[str]]
    _partitioning: Optional[Level] = None

    def _create_aggregated_measure(
        self, measure: MeasureDescription, agg_fun: str
    ) -> MeasureDescription:
        back_offset, forward_offset = (
            CumulativeTimeWindow._parse_time_period(self._window)
            if self._window
            else (None, None)
        )

        return GenericMeasure(
            "TIME_PERIOD_AGGREGATION",
            measure,
            self._level,
            back_offset,
            forward_offset,
            agg_fun,
        )

    @staticmethod
    def _parse_time_period(
        time_period: Tuple[Optional[str], Optional[str]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert the time period into a backward offset and a forward offset."""
        back = time_period[0]
        forward = time_period[1]
        return (
            # Drop the `-` sign.
            back[1:] if back is not None else None,
            forward if forward is not None else None,
        )


@dataclass(frozen=True)
class SiblingsWindow(Window):
    """Implementation of a Window for sibling aggregations.

    It contains at least hierarchy, and whether to exclude the current member from the calculations (useful when computing marginal aggregations).
    """

    _hierarchy: Hierarchy
    _exclude_self: bool = False

    def _create_aggregated_measure(
        self, measure: MeasureDescription, agg_fun: str
    ) -> MeasureDescription:
        return GenericMeasure(
            "SIBLINGS_AGG",
            measure,
            self._hierarchy,
            agg_fun,
            self._exclude_self,
        )


@dataclass(frozen=True)
class LeafLevels(Scope):
    """A collection of levels or level names, used in dynamic aggregation operations."""

    _levels: Collection[Level]

    @property
    def levels(self):
        """Dynamic aggregation levels."""
        return self._levels
