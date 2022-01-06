import datetime
from typing import Any, Collection, Dict, Iterable, List, Mapping, Union, cast

from py4j.java_collections import JavaArray, JavaMap, ListConverter
from py4j.java_gateway import JavaClass, JavaGateway, JavaObject


# No type stubs for py4j, so we ignore this error
def to_java_object_array(
    collection: Collection[Any],
    *,
    gateway: JavaGateway,  # type: ignore
) -> JavaArray:
    """Transform the Python collection into a Java array."""
    return to_typed_java_array(
        collection, gateway=gateway, array_type=gateway.jvm.Object
    )


def to_java_map(
    mapping: Mapping[Any, Any],
    *,
    gateway: JavaGateway,  # type: ignore
) -> JavaMap:
    """Convert a Python mapping to a JavaMap preserving the order of the keys."""
    return _to_typed_java_map(mapping, gateway=gateway, clazz="java.util.LinkedHashMap")


def _to_typed_java_map(
    to_convert: Mapping[Any, Any],
    *,
    gateway: JavaGateway,  # type: ignore
    clazz: str,
) -> JavaMap:
    """Convert to a map of the given type."""
    map_type = JavaClass(clazz, gateway._gateway_client)
    java_map = cast(JavaMap, map_type())
    for key in to_convert.keys():
        java_map[key] = as_java_object(to_convert[key], gateway=gateway)
    return java_map


def to_java_string_array(
    collection: Collection[str],
    *,
    gateway: JavaGateway,  # type: ignore
) -> JavaArray:
    """Transform the Python collection into a Java array of strings."""
    return to_typed_java_array(
        collection, gateway=gateway, array_type=gateway.jvm.String
    )


def to_java_object_list(
    iterable: Iterable[Any],
    *,
    gateway: JavaGateway,  # type: ignore
) -> Any:
    """Transform the Python iterable into a Java list of object."""
    return ListConverter().convert(
        [as_java_object(e, gateway=gateway) for e in iterable], gateway._gateway_client
    )


def to_typed_java_array(
    collection: Collection[Any],
    *,
    gateway: JavaGateway,  # type: ignore
    array_type: Any,
) -> JavaArray:
    """Transform to Java array of given type."""
    array = cast(JavaArray, gateway.new_array(array_type, len(collection)))
    if collection:
        for index, elem in enumerate(collection):
            array[index] = as_java_object(elem, gateway=gateway)
    return array


def to_java_date(
    date: Union[datetime.date, datetime.datetime],
    *,
    gateway: JavaGateway,  # type: ignore
) -> JavaObject:
    """Transform the Python date into a Java one."""
    if isinstance(date, datetime.datetime):
        if not date.tzinfo:
            return gateway.jvm.java.time.LocalDateTime.of(  # type: ignore
                date.year,
                date.month,
                date.day,
                date.hour,
                date.minute,
                date.second,
                date.microsecond * 1000,
            )
        raise NotImplementedError()
    return gateway.jvm.java.time.LocalDate.of(date.year, date.month, date.day)  # type: ignore


def as_java_object(
    arg: Any,
    *,
    gateway: JavaGateway,  # type: ignore
) -> Any:
    """Try to convert the arg to a java argument.

    Args:
        gateway: the Java gateway
        arg: the argument to convert.

    """
    if isinstance(arg, (datetime.date, datetime.datetime)):
        return to_java_date(arg, gateway=gateway)
    if isinstance(arg, list):
        # Convert to Vector
        vector_package = gateway.jvm.com.qfs.vector.array.impl  # type: ignore
        if all(isinstance(x, float) for x in arg):
            array = to_typed_java_array(
                arg, gateway=gateway, array_type=gateway.jvm.double
            )
            return vector_package.ArrayDoubleVector(array)  # type: ignore
        if all(isinstance(x, int) for x in arg):
            array = to_typed_java_array(
                arg, gateway=gateway, array_type=gateway.jvm.long
            )
            return vector_package.ArrayLongVector(array)  # type: ignore
        array = to_java_object_array(arg, gateway=gateway)
        return vector_package.ArrayObjectVector(array)  # type: ignore
    return arg


def to_python_dict(
    java_map: JavaMap,  # type: ignore
) -> Dict[Any, Any]:
    """Convert a Java map to a Python dict."""
    return {key: java_map[key] for key in java_map.keySet().toArray()}  # type: ignore


def to_python_list(
    list_to_convert: JavaObject,  # type: ignore
) -> List[Any]:
    """Convert a Java list to a Python list."""
    # ignore types when calling a Java function
    return list(list_to_convert.toArray())  # type: ignore
