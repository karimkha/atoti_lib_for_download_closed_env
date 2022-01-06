from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from typeguard import typechecked, typeguard_ignore

if TYPE_CHECKING:
    from ._java_api import JavaApi
    from ._local_cube import LocalCube


@typeguard_ignore
@dataclass
class AggregatesCache:
    """The aggregates cache associated with a cube."""

    _java_api: JavaApi = field(repr=False)
    _cube: LocalCube = field(repr=False)

    @property
    def capacity(self) -> int:
        """Capacity of the cache.

        It is the number of ``{location: measure}`` pairs of all the aggregates that can be stored.

        A strictly negative value will disable caching.

        A zero value will enable sharing but no caching.
        This means that queries will share their computations if they are executed at the same time, but the aggregated values will not be stored to be retrieved later.
        """
        return self._java_api.get_aggregates_cache_description(self._cube).capacity

    @capacity.setter
    @typechecked
    def capacity(self, capacity: int) -> None:
        """Capacity setter."""
        self._java_api.set_aggregates_cache(self._cube, capacity)
