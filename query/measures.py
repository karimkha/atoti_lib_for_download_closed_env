from .._base._base_measures import BaseMeasures
from .._mappings import ImmutableMapping
from .measure import QueryMeasure


class QueryMeasures(ImmutableMapping[str, QueryMeasure], BaseMeasures[QueryMeasure]):
    """Manage the query measures."""
