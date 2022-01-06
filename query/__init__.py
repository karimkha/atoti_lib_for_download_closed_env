"""
There are two main ways to query atoti sessions in Python:

* by passing measures and levels to :meth:`atoti.cube.Cube.query`
* by passing an MDX string to :meth:`atoti.session.Session.query_mdx`

:func:`atoti.open_query_session`, :meth:`atoti.query.cube.QueryCube.query`, and :meth:`atoti.query.session.QuerySession.query_mdx` can be used to query sessions started from remote atoti processes or classic ActivePivot (version >= 5.7) servers.
"""

from ._auth import create_basic_authentication, create_token_authentication

__all__ = ["create_basic_authentication", "create_token_authentication"]
