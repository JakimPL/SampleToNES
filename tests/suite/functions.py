from functools import partial
from typing import Callable


def compare_functions(function1: Callable, function2: Callable) -> bool:
    if isinstance(function1, partial):
        if not isinstance(function2, partial):
            return False

        return compare_functions(function1.func, function2.func) and function1.keywords == function2.keywords

    return function1 == function2
