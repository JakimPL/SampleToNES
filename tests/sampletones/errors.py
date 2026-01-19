import inspect
from re import Pattern
from typing import Any, Callable, Optional, Union

import pytest


def expect_error(
    function: Callable[..., Any],
    expected: Any,
    *args: Any,
    match: Optional[Union[str, Pattern[str]]] = None,
    **kwargs: Any,
) -> bool:
    if inspect.isclass(expected) and issubclass(expected, BaseException):
        assert isinstance(expected, type)
        with pytest.raises(expected, match=match):
            function(*args, **kwargs)

        return True

    return False
