from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

# https://packaging.python.org/guides/creating-and-discovering-plugins/#using-package-metadata
# The “selectable” entry points were introduced in importlib_metadata 3.6 and Python 3.10.
# Prior to those changes, entry_points accepted no parameters and always returned a dictionary of entry points
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points, version
else:
    from importlib.metadata import entry_points, version

if TYPE_CHECKING:
    from .query.session import QuerySession

NO_PLUGINS_FILTER = "no-plugins"

PLUGIN_FILTER_ENV_VAR = "_ATOTI_PLUGIN_FILTER"
"""Indicate which plugins to activate:

* If ``None``, all installed plugins are activated.
* If ``NO_PLUGINS_FILTER``, activate no plugins.
* Else this must be a plugin key corresponding to the only plugin to activate.
  For instance: ``"aws"``.
"""


class Plugin(ABC):
    """Atoti Plugin."""

    @abstractmethod
    def static_init(self):
        """Init called once when the plugin module is imported.

        It can be used to monkey patch the public API to plug the real functions.
        """

    @abstractmethod
    def get_jar_path(self) -> Optional[Path]:
        """Return the path to the JAR."""

    @abstractmethod
    def init_session(self, session: Any):
        """Init called every time a session is created.

        It can be used to call some internal Java function to initialize the plugin.
        """

    @abstractmethod
    def init_query_session(self, query_session: QuerySession):
        """Init called every time a query session is created.

        It can be used to call Python functions to initialize the plugin.
        """


class MissingPluginError(ImportError):
    """Error thrown when a plugin is missing."""

    def __init__(self, plugin_key: str):
        plugin_name = f"atoti-{plugin_key}"
        message = f"The {plugin_name} plugin is missing, install it and try again."
        super().__init__(message)


def _find_active_plugins(
    *,
    plugin_filter: Optional[str] = None,
) -> Dict[str, Plugin]:
    """Find the active plugins."""
    atoti_version = version("atoti")
    plugins = {}
    for entry_point in entry_points(group="atoti.plugins"):
        if plugin_filter is None or entry_point.name == plugin_filter:
            plugin_package_name = f"atoti-{entry_point.name}"
            plugin_version = version(plugin_package_name)
            if atoti_version != plugin_version:
                raise RuntimeError(
                    f"Cannot load plugin {plugin_package_name} v{plugin_version} because it does not have the same version as atoti (v{atoti_version})."
                )
            plugin_class = entry_point.load()
            plugins[entry_point.name] = plugin_class()

    return plugins


@lru_cache()
def get_active_plugins() -> Dict[str, Plugin]:
    """Return all the active plugins."""
    plugin_filter = os.environ.get(PLUGIN_FILTER_ENV_VAR)

    return (
        {}
        if plugin_filter == NO_PLUGINS_FILTER
        else _find_active_plugins(plugin_filter=plugin_filter)
    )


def is_plugin_active(plugin_key: str) -> bool:
    """Return whether the plugin is active or not."""
    return plugin_key in get_active_plugins()


def register_active_plugins():
    """Register all the active plugins."""
    for plugin in get_active_plugins().values():
        plugin.static_init()


def ensure_plugin_active(plugin_key: str):
    if not is_plugin_active(plugin_key):
        raise MissingPluginError(plugin_key)
