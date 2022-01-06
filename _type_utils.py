import copy
import functools
import inspect
from typing import (
    Any,
    Callable,
    Collection,
    Generic,
    Optional,
    TypeVar,
    Union,
    overload,
)

import typeguard
from typing_extensions import Literal

from ._api_utils import ContainerType, walk_api
from .measure import Measure
from .type import DataType

# pylint: disable=invalid-name
PercentileInterpolation = Literal["linear", "higher", "lower", "nearest", "midpoint"]
PercentileIndexInterpolation = Literal["higher", "lower", "nearest"]
PercentileMode = Literal["simple", "centered", "inc", "exc"]
VarianceMode = Literal["sample", "population"]
# pylint: enable=invalid-name

F = TypeVar("F", bound=Callable[..., Any])  # pylint: disable=invalid-name


def _instrument_typechecking(
    container: ContainerType,
    include_attribute: Optional[
        Callable[[ContainerType, str, Collection[str]], bool]
    ] = None,
):
    def callback(container: ContainerType, attribute_name: str):
        func = getattr(container, attribute_name)

        # Bound methods cannot be instrumented.
        if inspect.ismethod(func) and not _is_typechecked(func):
            raise RuntimeError(f"Missing type checking for bound method {func}")

        new_func = typecheck()(func)
        if new_func is not func:
            setattr(container, attribute_name, new_func)

    walk_api(container, callback=callback, include_attribute=include_attribute)


def _is_typechecked(func: Callable[..., Any]) -> bool:
    return getattr(func, "_typechecked", False)


def _mark_typechecked(func: Callable[..., Any]):
    setattr(func, "_typechecked", True)


@overload
def typecheck(func: F) -> F:
    """Perform runtime type checking on the decorated function."""
    ...


@overload
def typecheck(
    *,
    ignored_params: Optional[Collection[str]] = None,
) -> Callable[[F], F]:
    """Return a decorator that will perform runtime type checking on the decorated function.

    Args:
        ignored_params: A collection of parameter names that will not be type checked.
    """
    ...


@overload
def typecheck(clazz: type) -> type:
    """Perform runtime type checking on the public API of the decorated class."""
    ...


def typecheck(  # type: ignore
    target: Optional[Union[F, type]] = None,
    *,
    ignored_params: Optional[Collection[str]] = None,
) -> Union[F, Callable[[F], F], type]:
    """Decorate the target to perform dynamic type checking.

    Use the more specific overloaded functions depending on the decorated argument.
    """
    if not target:
        return _typecheck_function(ignored_params=ignored_params)
    if inspect.isfunction(target) or inspect.ismethod(target):
        return _typecheck_function()(target)
    if isinstance(target, type):
        return _typecheck_class(target)

    raise TypeError(f"Unexpected type {type(target)} of {target}")


def _typecheck_function(
    *, ignored_params: Optional[Collection[str]] = None
) -> Callable[[F], F]:
    """Perform runtime type checking on the parameters of the decorated function.

    Args:
        ignored_params: A collection of parameter names that will not be type checked.
    """

    def decorator(func: F) -> F:
        # Verify whether we need to perform type checking.
        if not getattr(func, "__annotations__", None):
            # No type annotations. Ignore this method.
            return func
        if _is_typechecked(func):
            # Already typechecked.
            return func

        # Create and return the wrapper.
        return _TypecheckWrapperFactory(func, ignored_params).create_wrapper()

    return decorator


def _typecheck_class(clazz: type) -> type:
    """Perform runtime type checking on the public API of the decorated class."""
    # Consider all public symbols of the class.
    def include_attribute(  # pylint: disable=too-many-positional-parameters
        container: ContainerType, attribute_name: str, exported_names: Collection[str]
    ) -> bool:
        # Sanity checks
        if container is not clazz:
            raise RuntimeError(f"Unexpected container for {clazz}: {container}")
        if exported_names:
            raise RuntimeError(
                f"Unexpected exported names for {container}: {exported_names}"
            )

        # Only consider public functions / methods.
        element = getattr(container, attribute_name)
        if inspect.isfunction(element) or inspect.ismethod(element):
            return not attribute_name.startswith("_")

        return False

    # Instrument the class and return it.
    _instrument_typechecking(clazz, include_attribute)
    return clazz


class _TypecheckWrapperFactory(Generic[F]):
    def __init__(self, func: F, ignored_params: Optional[Collection[str]]) -> None:
        self._func = func

        # Unwrap the function for type checking.
        # Make sure that the function is not already typed checked.
        self._ts_func = inspect.unwrap(func, stop=_is_typechecked)
        if _is_typechecked(self._ts_func):
            raise RuntimeError(f"{func} is already typed checked.")

        # Create a copy of the function for typechecking if necessary.
        if ignored_params:
            self._ts_func = copy.copy(self._ts_func)
            setattr(
                self._ts_func,
                "__annotations__",
                {
                    param: annotation
                    for param, annotation in self._ts_func.__annotations__.items()
                    if param not in ignored_params
                },
            )

    def create_wrapper(self) -> Any:
        # Create the wrapper function.
        @functools.wraps(self._func)
        def typechecked_func_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Perform typechecking on the input arguments.
            memo = typeguard._CallMemo(func=self._ts_func, args=args, kwargs=kwargs)
            typeguard.check_argument_types(memo)

            # Call the actual function.
            return self._func(*args, **kwargs)

        # Mark the function as typechecked and return it.
        _mark_typechecked(typechecked_func_wrapper)
        return typechecked_func_wrapper


class DataTypeError(TypeError):
    """Error raised when a measure does not have the expected type."""

    def __init__(
        self,
        measure: Measure,
        expected_type: Union[DataType, str],
    ):
        """Create the type error.

        Args:
            measure: The measure with wrong type.
            expected_type: Expected type.

        """
        super().__init__(
            "Incorrect measure type."
            f" Expected measure {measure.name} to be of type {expected_type}"
            f" but got {measure.data_type}."
        )


def is_array(data_type: DataType) -> bool:
    return data_type.java_type.endswith("[]")


def is_temporal(data_type: DataType) -> bool:
    return (
        "date" in data_type.java_type.lower() or "time" in data_type.java_type.lower()
    )


def is_date(data_type: DataType) -> bool:
    return "date" in data_type.java_type.lower()
