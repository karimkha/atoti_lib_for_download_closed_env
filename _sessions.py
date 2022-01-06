from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from types import TracebackType
from typing import Any, Dict, Mapping, Optional, Type, Union

from ._mappings import EMPTY_MAPPING, DelegateMutableMapping
from ._repr_utils import ReprJson, ReprJsonable
from ._type_utils import typecheck
from .config import SessionConfig
from .experimental._distributed.session import DistributedSession
from .query.auth import Auth
from .query.session import QuerySession
from .session import Session

_Session = Union[Session, DistributedSession, QuerySession]


@dataclass(frozen=True)
class SessionPrivateParameters:
    detached_process: bool = False


@dataclass(frozen=True)
class Sessions(DelegateMutableMapping[str, _Session], ReprJsonable):
    """Manage the sessions."""

    _sessions: Dict[str, _Session] = field(default_factory=dict)

    def _get_underlying(self) -> Dict[str, _Session]:
        """Get the underlying mapping."""
        self._remove_closed_sessions()
        return self._sessions

    @typecheck
    def create_session(
        self,
        name: str = "Unnamed",
        *,
        config: Mapping[str, Any] = EMPTY_MAPPING,
        **kwargs: Any,
    ) -> Session:
        """Create a session.

        Args:
            name: The name of the session.
            config: The configuration of the session as a plain Python object.
                For a complete list of all the configuration keys available, see :class:`atoti.config.session_config.SessionConfig`.

        Example:

          .. code-block::

              session = tt.create_session(
                  config={
                      "port": 9090,
                      "user_content_storage": "./content",
                      "java_options": ["-Xms1g", "-verbose:gc", "-XX:+UsuG1GC"],
                      "logging": {"destination": "./atoti/server.log"},
                  },
              )
        """
        self._clear_duplicate_sessions(name)
        session = Session(
            name,
            config=SessionConfig._from_mapping(config or {}),
            **asdict(SessionPrivateParameters(**kwargs)),
        )
        self._sessions[name] = session
        return session

    @typecheck
    def _create_distributed_session(
        self,
        name: str,
        *,
        config: Mapping[str, Any] = EMPTY_MAPPING,
        **kwargs: Any,
    ) -> DistributedSession:
        self._clear_duplicate_sessions(name)
        session = DistributedSession(
            name,
            config=SessionConfig._from_mapping(config or {}),
            **asdict(SessionPrivateParameters(**kwargs)),
        )
        self[name] = session
        return session

    @typecheck
    def open_query_session(
        self, url: str, name: Optional[str] = None, *, auth: Optional[Auth] = None
    ) -> QuerySession:
        """Open an existing session to query it.

        This can be used to connect to:

          * Other sessions with another atoti process.
          * ActivePivot cubes built with a classic Java project, if version >= 5.7.0.

        Args:
            url: The server base URL.
                ``{url}/versions/rest`` is expected to exist.
            name: The name to give to the session.
                Defaults to the passed *url* argument.
            auth: The authentication to use.
                It is a function taking the request URL and returning a dictionary of HTTP headers
                to include in the request.

                Example::

                    auth=lambda url: {"Authorization": f"Bearer {token}"}

                There are some built-in helpers: :func:`atoti.query.create_basic_authentication` and :func:`atoti.query.create_token_authentication`.
        """
        name = name or url
        self._clear_duplicate_sessions(name)
        query_session = QuerySession(url, auth=auth, name=name)
        self[name] = query_session
        return query_session

    def _clear_duplicate_sessions(self, name: str):
        if name in self._sessions:
            logging.getLogger("atoti.session").warning(
                """Deleting existing "%s" session to create the new one.""", name
            )
            del self[name]

    def __enter__(self) -> Sessions:
        return self

    def __exit__(  # pylint: disable=too-many-positional-parameters
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close all the opened sessions."""
        for session in self._sessions.values():
            if isinstance(session, Session):
                session.close()

    def _remove_closed_sessions(self) -> None:
        sessions_to_remove = [
            session
            for session in self._sessions.values()
            if isinstance(session, Session) and session.closed
        ]
        for session in sessions_to_remove:
            del self._sessions[session.name]

    def _update(self, mapping: Mapping[str, _Session]):
        self._remove_closed_sessions()
        for session_name, session in mapping.items():
            if session_name in self._sessions:
                del self[session_name]
            self._sessions[session_name] = session

    def __getitem__(self, key: str) -> _Session:
        """Get a session."""
        self._remove_closed_sessions()
        return self._sessions[key]

    def __delitem__(self, key: str) -> None:
        """Remove a session.

        This method also stops the Java session, destroying all Java objects attached to it.
        """
        self._remove_closed_sessions()
        if key in self._sessions:
            session = self._sessions[key]
            if isinstance(session, Session):
                session.close()
            del self._sessions[key]

    def _repr_json_(self) -> ReprJson:
        return (
            {name: session._repr_json_()[0] for name, session in sorted(self.items())},
            {"root": "Sessions", "expanded": False},
        )
