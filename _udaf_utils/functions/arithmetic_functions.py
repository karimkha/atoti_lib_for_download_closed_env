"""Java function implementations for arithmetic operations."""
from ..java_function import ExistingJavaFunction

ATOTI_OPERATOR_PACKAGE = "io.atoti.udaf.operators"

ADD_FUNCTION = ExistingJavaFunction(
    "ArithmeticOperator.add",
    import_package=ATOTI_OPERATOR_PACKAGE,
)

SUB_FUNCTION = ExistingJavaFunction(
    "ArithmeticOperator.minus",
    import_package=ATOTI_OPERATOR_PACKAGE,
)

TRUEDIV_FUNCTION = ExistingJavaFunction(
    "ArithmeticOperator.divide",
    import_package=ATOTI_OPERATOR_PACKAGE,
)

MUL_FUNCTION = ExistingJavaFunction(
    "ArithmeticOperator.multiply",
    import_package=ATOTI_OPERATOR_PACKAGE,
)
