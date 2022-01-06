import inspect
from types import ModuleType
from typing import Any, Callable, Collection, Iterable, Mapping, Optional, Set, Union

from ._mappings import EMPTY_MAPPING

ContainerType = Union[type, ModuleType]


def get_container_full_name(container: ContainerType) -> str:
    container_module = inspect.getmodule(container)

    if container_module is None:
        raise RuntimeError("Expected container to have a module.")

    prefix = "" if inspect.ismodule(container) else f"{container_module.__name__}."
    return f"{prefix}{container.__name__}"


def decorate(
    *,
    container: ContainerType,
    attribute_name: str,
    decorator: Callable[..., Callable[..., Any]],
    decorator_args: Iterable[Any] = (),
    decorator_kwargs: Mapping[str, Any] = EMPTY_MAPPING,
) -> None:
    func = getattr(container, attribute_name)
    new_func = decorator(
        func,
        *decorator_args,
        **decorator_kwargs,
    )
    setattr(container, attribute_name, new_func)


def is_private_element(element_name: str) -> bool:
    return element_name.startswith("_")


def _is_dunder_method(method_name: str) -> bool:
    return method_name.startswith("__") and method_name.endswith("__")


def _is_plugin(method_module: str):
    return method_module.startswith("atoti_")


def _is_exported_element(
    element: Any,
    *,
    elem_container_module: Optional[ModuleType],
    elem_module: Optional[ModuleType],
    exported_names: Collection[str],
) -> bool:
    try:
        if not elem_module:
            return False

        is_part_of_atoti = elem_module.__name__.startswith("atoti")

        if not is_part_of_atoti:
            return False

        full_name = f"{elem_module.__name__}.{element.__name__}"

        is_monkey_patched_method_by_plugin = (
            elem_container_module is not None
            and _is_plugin(full_name)
            and not _is_plugin(elem_container_module.__name__)
        )

        if is_monkey_patched_method_by_plugin:
            return True

        is_in_private_module = "._" in full_name

        if is_in_private_module:
            return element.__name__ in exported_names or _is_dunder_method(
                element.__name__
            )
        return True

    except AttributeError:
        return False


def _walk_api(
    container: ContainerType,
    *,
    callback: Callable[[ContainerType, str], None],
    include_attribute: Optional[
        Callable[[ContainerType, str, Collection[str]], bool]
    ] = None,
    visited_elements: Set[str],
):
    # Retrieve the symbols explicitely exported by the container (if any).
    exported_names = getattr(container, "__all__", [])

    # Recursively iterate through all the attributes of the container to find public functions.
    for attribute_name in dir(container):
        element = getattr(container, attribute_name)

        # Make sure the element has not been visited already.
        full_name = f"{container.__name__}.{attribute_name}"
        if full_name in visited_elements:
            continue
        visited_elements.add(full_name)
        # Make sure the element should be considered.
        if include_attribute:
            if not include_attribute(container, attribute_name, exported_names):
                continue
        elif not _is_exported_element(
            element,
            elem_container_module=inspect.getmodule(container),
            elem_module=inspect.getmodule(element),
            exported_names=exported_names,
        ):
            continue

        # Follow "container" types.
        if inspect.ismodule(element) or inspect.isclass(element):
            _walk_api(
                element,
                callback=callback,
                visited_elements=visited_elements,
            )
            continue

        # Invoke the callback on functions.
        if inspect.isfunction(element) or inspect.ismethod(element):
            callback(container, attribute_name)
            continue

        # What is this?
        raise RuntimeError(f"Unexpected element {element}")


def walk_api(
    container: ContainerType,
    *,
    callback: Callable[[ContainerType, str], None],
    include_attribute: Optional[
        Callable[[ContainerType, str, Collection[str]], bool]
    ] = None,
):
    """Recursively explore the public API of the input container.

    Args:
        container: The container to explore.
        callback: The callback to invoke on all public functions.
            It takes the parent container of the exposed function and the function name as arguments.
        include_attribute: A function that returns whether the callback function should be invoked on the given attribute of the container.
            It takes the container attribute as input.
            If ``None``, this defaults to calling :func:`_is_exported_element` on the attribute.
    """
    visited_elements = set()
    _walk_api(
        container,
        callback=callback,
        include_attribute=include_attribute,
        visited_elements=visited_elements,
    )
