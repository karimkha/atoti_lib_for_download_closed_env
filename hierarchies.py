from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Iterable, Mapping, Tuple, Union

from typeguard import typechecked, typeguard_ignore

from ._base._base_hierarchies import _HierarchyKey
from ._local_hierarchies import LocalHierarchies
from .hierarchy import Hierarchy
from .level import Level
from .table import Column

if TYPE_CHECKING:
    from .cube import Cube

LevelOrColumn = Union[Level, Column]


@typeguard_ignore
@dataclass(frozen=True)
class Hierarchies(LocalHierarchies[Hierarchy]):
    """Manage the hierarchies.


    Example:
        >>> prices_df = pd.DataFrame(
        ...     columns=["Nation", "City", "Color", "Price"],
        ...     data=[
        ...         ("France", "Paris", "red", 20.0),
        ...         ("France", "Lyon", "blue", 15.0),
        ...         ("France", "Toulouse", "green", 10.0),
        ...         ("UK", "London", "red", 20.0),
        ...         ("UK", "Manchester", "blue", 15.0),
        ...     ],
        ... )
        >>> table = session.read_pandas(prices_df, table_name="Prices")
        >>> cube = session.create_cube(table, mode="manual")
        >>> h = cube.hierarchies
        >>> h["Nation"] = {"Nation": table["Nation"]}
        >>> list(h.keys())
        [('Prices', 'Nation')]

    A hierarchy can be renamed by creating a new one with the same levels and then removing the old one.

        >>> h["Country"] = h["Nation"].levels
        >>> del h["Nation"]
        >>> list(h.keys())
        [('Prices', 'Country')]

    The :meth:`~dict.update` method is overridden to batch hierarchy creation operations for improved performance:

        >>> h.update(
        ...     {
        ...         ("Geography", "Geography"): [table["Nation"], table["City"]],
        ...         "Color": {"Color": table["Color"]},
        ...     }
        ... )
        >>> list(h.keys())
        [('Prices', 'Color'), ('Geography', 'Geography'), ('Prices', 'Country')]
    """

    _cube: Cube = field(repr=False)

    def _get_underlying(self) -> Dict[Tuple[str, str], Hierarchy]:
        return self._retrieve_hierarchies(self._java_api, self._cube)

    @typechecked
    def __getitem__(self, key: _HierarchyKey) -> Hierarchy:
        (dimension_name, hierarchy_name) = self._convert_key(key)
        hierarchies = self._java_api.retrieve_hierarchy(
            hierarchy_name,
            cube=self._cube,
            dimension=dimension_name,
        )
        if len(hierarchies) == 0:
            raise KeyError(f"Unknown hierarchy: {key}")
        if len(hierarchies) == 1:
            return hierarchies[0]
        raise self._multiple_hierarchies_error(key, hierarchies)

    @typechecked
    def __setitem__(  # type: ignore
        self,
        key: _HierarchyKey,
        value: Union[Iterable[LevelOrColumn], Mapping[str, LevelOrColumn]],
    ) -> None:
        self.update({key: value})

    @typechecked
    def __delitem__(self, key: _HierarchyKey) -> None:
        try:
            self._java_api.drop_hierarchy(self._cube, self[key])
            self._java_api.refresh()
        except KeyError:
            raise KeyError(f"{key} is not an existing hierarchy.") from None

    def _update(  # type: ignore
        self,
        hierarchies: Mapping[_HierarchyKey, Mapping[str, LevelOrColumn]],
    ) -> None:
        structure = {}
        for hierarchy_key, levels_or_columns in hierarchies.items():
            dimension_name, hierarchy_name = self._get_dimension_and_hierarchy_name(
                hierarchy_key, levels_or_columns
            )
            if dimension_name not in structure:
                structure[dimension_name] = {}
            structure[dimension_name].update(
                {hierarchy_name: _get_hierarchy_levels(levels_or_columns)}
            )
        self._java_api.update_hierarchies_for_cube(self._cube, structure=structure)
        self._java_api.refresh()

    def update(  # type: ignore
        self,
        hierarchies: Union[
            Mapping[
                _HierarchyKey,
                Union[Iterable[LevelOrColumn], Mapping[str, LevelOrColumn]],
            ],
            Iterable[
                Tuple[
                    _HierarchyKey,
                    Union[Iterable[LevelOrColumn], Mapping[str, LevelOrColumn]],
                ]
            ],
        ],
        **kwargs: Union[Iterable[LevelOrColumn], Mapping[str, LevelOrColumn]],
    ) -> None:
        """This method batches the updates for improved performance."""
        full_hierarchies = {}
        full_hierarchies.update(hierarchies, **kwargs)
        final_hierarchies: Mapping[_HierarchyKey, Mapping[str, LevelOrColumn]] = {
            hierarchy_key: _normalize_levels(levels_or_columns)
            for hierarchy_key, levels_or_columns in full_hierarchies.items()
        }
        self._update(final_hierarchies)

    def _get_dimension_and_hierarchy_name(
        self,
        hierarchy_key: _HierarchyKey,
        levels_or_columns: Mapping[str, LevelOrColumn],
    ) -> Tuple[str, str]:
        dimension_name, hierarchy_name = self._convert_key(hierarchy_key)
        if dimension_name is None:
            hierarchies = self._java_api.retrieve_hierarchy(
                hierarchy_name, cube=self._cube, dimension=None
            )
            if len(hierarchies) > 1:
                raise self._multiple_hierarchies_error(hierarchy_name, hierarchies)
            first_item = list(levels_or_columns.values())[0]
            if isinstance(first_item, Level):
                dimension_name = first_item.dimension
            else:
                dimension_name = first_item._table.name
        return dimension_name, hierarchy_name


def _normalize_levels(
    levels_or_columns: Union[Iterable[LevelOrColumn], Mapping[str, LevelOrColumn]]
) -> Mapping[str, LevelOrColumn]:
    return (
        levels_or_columns
        if isinstance(levels_or_columns, Mapping)
        else {
            level_or_column.name: level_or_column
            for level_or_column in levels_or_columns
        }
    )


def _get_hierarchy_levels(
    levels_or_columns: Mapping[str, LevelOrColumn]
) -> Mapping[str, str]:
    return {
        level_name: level_or_column._column_name
        if isinstance(level_or_column, Level)
        else level_or_column.name
        for (level_name, level_or_column) in levels_or_columns.items()
    }
