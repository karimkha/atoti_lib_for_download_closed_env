from __future__ import annotations

import atexit
import functools
import json
import os
import platform
import time
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from types import ModuleType
from typing import Any, Callable, Optional
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from ._api_utils import (
    ContainerType,
    decorate,
    get_container_full_name,
    is_private_element,
    walk_api,
)
from ._os_utils import get_env_flag
from ._path_utils import get_atoti_home
from ._plugins import is_plugin_active
from ._version import VERSION

DISABLE_TELEMETRY_ENV_VAR = "ATOTI_DISABLE_TELEMETRY"

TEST_TELEMETRY_ENV_VAR = "ATOTI_TEST_TELEMETRY"

# Path where the installation's unique ID is stored.
_INSTALLATION_ID_PATH = get_atoti_home() / "installation_id.txt"

_TELEMETRY_SERVICE_URL = "https://telemetry.atoti.io/events"

TELEMETRY_ASYNC_EXECUTOR = ThreadPoolExecutor(max_workers=1)


@dataclass(frozen=True)
class TelemetryEvent(ABC):

    event_type: str = field(init=False)

    def _set_event_type(self, event_type: str):
        # The dataclass is frozen, so we can't assign to this field directly
        object.__setattr__(self, "event_type", event_type)


@dataclass(frozen=True)
class ImportEvent(TelemetryEvent):
    """Triggered when the library is imported."""

    installation_id: str
    operating_system: str
    python_version: str
    version: str
    environment: Optional[str]

    def __post_init__(self) -> None:
        self._set_event_type("import")


@dataclass(frozen=True)
class ExitEvent(TelemetryEvent):
    """Triggered when the Python process terminates."""

    duration: timedelta

    def __post_init__(self) -> None:
        self._set_event_type("exit")


@dataclass(frozen=True)
class CallEvent(TelemetryEvent):
    """Triggered when a function or method from the public API is called."""

    path: str
    duration: timedelta

    def __post_init__(self):
        self._set_event_type("call")


def _send_event_to_telemetry_service(event: TelemetryEvent):
    action: Callable[..., Any] = urlopen
    data = json.dumps({"events": [asdict(event)]}, default=str).encode("utf8")
    payload = Request(
        _TELEMETRY_SERVICE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    if get_env_flag(TEST_TELEMETRY_ENV_VAR) is True:
        action = print
        payload = data.decode("utf8")

    TELEMETRY_ASYNC_EXECUTOR.submit(action, payload)


def disabled_by_atoti_plus() -> bool:
    return is_plugin_active("plus")


def disabled_by_environment_variable() -> bool:
    return get_env_flag(DISABLE_TELEMETRY_ENV_VAR)


def get_installation_id_from_file() -> Optional[str]:
    if not _INSTALLATION_ID_PATH.exists():
        return None

    try:
        content = _INSTALLATION_ID_PATH.read_text(encoding="utf8").strip()
        UUID(content)
        return content
    except:  # nosec  pylint: disable=bare-except
        # The file content is not a valid UUID.
        return None


def write_installation_id_to_file(installation_id: str):
    try:
        _INSTALLATION_ID_PATH.parent.mkdir(
            exist_ok=True,
            parents=True,
        )
        _INSTALLATION_ID_PATH.write_text(
            f"{installation_id}{os.linesep}", encoding="utf8"
        )
    except:  # nosec  pylint: disable=bare-except
        # Do nothing even if the id could not be written to the file.
        ...


def get_installation_id() -> str:
    existing_id = get_installation_id_from_file()

    if existing_id is not None:
        return existing_id

    new_id = str(uuid4())

    write_installation_id_to_file(new_id)

    return new_id


def _send_exit_event(*, imported_at: datetime) -> None:
    _send_event_to_telemetry_service(ExitEvent(duration=datetime.now() - imported_at))


@dataclass
class _CallTracker:
    tracking = False


def _call_with_tracking(
    func: Callable[..., Any],
    *args: Any,
    _atoti_tracked_container: ContainerType,
    **kwargs: Any,
) -> Any:
    call_time = time.perf_counter()

    try:
        return func(*args, **kwargs)
    finally:
        duration = timedelta(seconds=time.perf_counter() - call_time)
        call_event = CallEvent(
            path=f"{get_container_full_name(_atoti_tracked_container)}.{func.__name__}",
            duration=duration,
        )
        _send_event_to_telemetry_service(call_event)


def call_event_decorator(
    func: Callable[..., Any],
    *,
    tracked_container: ContainerType,
    call_tracker: _CallTracker,
) -> Callable:
    @functools.wraps(func)
    def function_wrapper(
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if call_tracker.tracking:
            return func(*args, **kwargs)

        call_tracker.tracking = True

        try:
            return _call_with_tracking(
                func, *args, _atoti_tracked_container=tracked_container, **kwargs
            )
        finally:
            call_tracker.tracking = False

    return function_wrapper


def _should_get_skipped(container: ContainerType, attribute_name: str) -> bool:
    element = getattr(container, attribute_name)
    return is_private_element(attribute_name) or (
        # `update()` is not a dunder method but it's part of the built-in methods of mutable mappings that should not be tracked.
        "." in element.__qualname__
        and element.__name__ == "update"
    )


def _walk_telemetrized_api(
    module: ModuleType,
    *,
    callback: Callable[[ContainerType, str], None],
):
    def _telemetry_filter(container: ContainerType, attribute_name: str) -> None:
        if _should_get_skipped(container, attribute_name):
            return
        callback(container, attribute_name)

    walk_api(module, callback=_telemetry_filter)


def _instrument_call_tracking(
    module: ModuleType,
) -> None:
    call_tracker = _CallTracker()

    def decorate_to_track_calls(container: ContainerType, attribute_name: str) -> None:
        decorate(
            container=container,
            attribute_name=attribute_name,
            decorator=call_event_decorator,
            decorator_kwargs={
                "tracked_container": container,
                "call_tracker": call_tracker,
            },
        )

    _walk_telemetrized_api(
        module,
        callback=decorate_to_track_calls,
    )


def setup_telemetry(module: ModuleType) -> None:
    if disabled_by_atoti_plus() or disabled_by_environment_variable():
        return

    imported_at = datetime.now()

    import_event = ImportEvent(
        operating_system=platform.platform(),
        installation_id=get_installation_id(),
        python_version=platform.python_version(),
        version=VERSION,
        environment="CI" if get_env_flag("CI") else None,
    )

    _send_event_to_telemetry_service(import_event)

    _instrument_call_tracking(module)

    atexit.register(_send_exit_event, imported_at=imported_at)
