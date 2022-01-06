from abc import abstractmethod
from typing import Any, Generic, TypeVar, cast
from uuid import uuid4

from .._ipython_utils import find_corresponding_top_level_variable_name
from .._plugins import MissingPluginError
from .._repr_utils import ReprJson, ReprJsonable
from ._base_cubes import BaseCubes

_BaseCubes = TypeVar("_BaseCubes", bound="BaseCubes")


class BaseSession(Generic[_BaseCubes], ReprJsonable):
    """Base class for session."""

    def __init__(self) -> None:
        self.__id = str(uuid4())

    def link(self, *args: Any, **kwargs: Any) -> Any:  # pylint: disable=no-self-use
        raise MissingPluginError("jupyterlab")

    @property
    @abstractmethod
    def cubes(self) -> _BaseCubes:
        """Cubes of the session."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the session."""

    def visualize(  # pylint: disable=no-self-use
        self, *args: Any, **kwargs: Any
    ) -> Any:
        raise MissingPluginError("jupyterlab")

    @property
    def _id(self) -> str:
        return self.__id

    def _get_widget_creation_code(self) -> str:
        session_variable_name = find_corresponding_top_level_variable_name(self)

        visualize_call = ".visualize()"

        if session_variable_name:
            return f"""{session_variable_name}{visualize_call}"""

        return f"""import atoti as tt\n\ntt.sessions["{self.name}"]{visualize_call}"""

    def _repr_json_(self) -> ReprJson:
        """Return the JSON representation of a session."""
        cubes = self.cubes._repr_json_()[0]
        data = (
            {"Tables": cast(Any, self).tables._repr_json_()[0], "Cubes": cubes}
            if hasattr(self, "tables")
            else {"Cubes": cubes}
        )
        return (
            data,
            {"expanded": False, "root": self.name},
        )
