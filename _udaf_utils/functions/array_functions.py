"""Java function implementation for array functions."""

from ..._operation import JavaFunctionOperation, Operation
from ...type import DOUBLE, DOUBLE_ARRAY
from ..java_function import CustomJavaFunction

sum_function = CustomJavaFunction(
    [("vector", DOUBLE_ARRAY)],
    method_name="array_sum",
    method_body="return vector.sumDouble();\n",
    output_type=DOUBLE,
)


def array_sum(operation: Operation) -> JavaFunctionOperation:
    return sum_function(operation)


mean_function = CustomJavaFunction(
    [("vector", DOUBLE_ARRAY)],
    method_name="array_mean",
    method_body="return vector.average();",
    output_type=DOUBLE,
)


def array_mean(operation: Operation) -> JavaFunctionOperation:
    return mean_function(operation)
