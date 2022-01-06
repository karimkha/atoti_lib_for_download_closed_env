import warnings


def deprecated(message: str) -> None:
    """Raise a warning to indicate that something is deprecated.

    Args:
        message: Explanation of the deprecation.
    """

    # Using FutureWarning instead of DeprecationWarning because
    # DeprecationWarnings are hidden by default in IPython.
    # pandas does the same.
    # See:
    #  - https://docs.python.org/3/library/warnings.html#warning-categories
    #  - https://github.com/ipython/ipython/issues/8478
    warnings.warn(message, category=FutureWarning, stacklevel=2)
