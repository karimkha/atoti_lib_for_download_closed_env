from dataclasses import dataclass
from typing import Any, Optional, Sequence


@dataclass(frozen=True)
class Comparator:
    """Level comparator."""

    _name: str
    _first_members: Optional[Sequence[Any]]


ASCENDING = Comparator("ASCENDING", None)
"""Level comparator for ascending order.

    The ascending order is used by default.
"""

DESCENDING = Comparator("DESCENDING", None)
"""Level comparator for descending order.

    Example:
        >>> df = pd.DataFrame(
        ...     {
        ...         "Date": ["2021-05-19", "2021-05-20"],
        ...         "Product": ["TV", "Smartphone"],
        ...         "Quantity": [12, 18],
        ...     }
        ... )
        >>> table = session.read_pandas(df, table_name="Sales")
        >>> cube = session.create_cube(table)
        >>> l, m = cube.levels, cube.measures
        >>> l["Date"].comparator == tt.comparator.ASCENDING
        True
        >>> cube.query(m["Quantity.SUM"], levels=[l["Date"]])
                   Quantity.SUM
        Date
        2021-05-19           12
        2021-05-20           18
        >>> l["Date"].comparator = tt.comparator.DESCENDING
        >>> cube.query(m["Quantity.SUM"], levels=[l["Date"]])
                   Quantity.SUM
        Date
        2021-05-20           18
        2021-05-19           12
"""


def first_members(*members: Any) -> Comparator:
    """Create a level comparator with the given first members.

    Example:
        >>> df = pd.DataFrame(
        ...     {
        ...         "Product": ["TV", "Smartphone", "Computer", "Screen"],
        ...         "Quantity": [12, 18, 50, 68],
        ...     }
        ... )
        >>> table = session.read_pandas(df, table_name="Products")
        >>> cube = session.create_cube(table)
        >>> l, m = cube.levels, cube.measures
        >>> cube.query(m["Quantity.SUM"], levels=[l["Product"]])
                   Quantity.SUM
        Product
        Computer             50
        Screen               68
        Smartphone           18
        TV                   12
        >>> l["Product"].comparator = tt.comparator.first_members("TV", "Screen")
        >>> cube.query(m["Quantity.SUM"], levels=[l["Product"]])
                   Quantity.SUM
        Product
        TV                   12
        Screen               68
        Computer             50
        Smartphone           18

    """
    return Comparator("FIRST_MEMBERS", list(members))
