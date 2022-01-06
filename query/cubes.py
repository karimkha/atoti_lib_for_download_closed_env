from .._base._base_cubes import BaseCubes
from .._mappings import ImmutableMapping
from .cube import QueryCube


class QueryCubes(ImmutableMapping[str, QueryCube], BaseCubes[QueryCube]):
    """Manage the query cubes."""
