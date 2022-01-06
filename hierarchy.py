from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping

from typeguard import typechecked, typeguard_ignore

from ._base._base_hierarchy import BaseHierarchy
from .level import Level

if TYPE_CHECKING:
    from ._java_api import JavaApi
    from ._local_cube import LocalCube
    from .hierarchies import Hierarchies
    from .levels import Levels
    from .measures import Measures


@typeguard_ignore
@dataclass(eq=False)
class Hierarchy(BaseHierarchy[Mapping[str, Level]]):
    """Hierarchy of a :class:`~atoti.cube.Cube`.

    A hierarchy is a sub category of a :attr:`~dimension` and represents a precise type of data.

    For example, :guilabel:`Quarter` or :guilabel:`Week` could be hierarchies in the :guilabel:`Time` dimension.
    """

    _name: str
    _levels: Mapping[str, Level]
    _dimension: str
    _slicing: bool
    _cube: LocalCube[Hierarchies, Levels, Measures] = field(repr=False)
    _java_api: JavaApi = field(repr=False)
    _visible: bool

    @property
    def levels(self) -> Mapping[str, Level]:
        return self._levels

    @property
    def dimension(self) -> str:
        return self._dimension

    @property
    def slicing(self) -> bool:
        return self._slicing

    @property
    def name(self) -> str:
        return self._name

    @property
    def visible(self) -> bool:
        """Whether the hierarchy is visible or not."""
        return self._visible

    @levels.setter
    @typechecked
    def levels(self, value: Mapping[str, Level]) -> None:
        """Levels setter."""
        self._levels = value
        self._cube.hierarchies.update({(self._dimension, self.name): value})

    @dimension.setter
    @typechecked
    def dimension(self, value: str) -> None:
        """Dimension setter."""
        self._java_api.update_hierarchy_coordinate(
            cube=self._cube, hierarchy=self, new_dim=value, new_hier=self._name
        )
        self._java_api.refresh()
        self._dimension = value

    @slicing.setter
    @typechecked
    def slicing(self, value: bool) -> None:
        """Slicing setter."""
        self._java_api.update_hierarchy_slicing(self, value)
        self._java_api.refresh()
        self._slicing = value

    @visible.setter
    @typechecked
    def visible(self, value: bool) -> None:
        """Visibility setter."""
        self._java_api.set_hierarchy_visibility(
            cube=self._cube, dimension=self._dimension, name=self._name, visible=value
        )
        self._java_api.refresh()
        self._visible = value
