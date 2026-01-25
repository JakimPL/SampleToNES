import inspect
from re import Pattern
from typing import Any, Callable, Optional, Tuple, Union

import pytest


def _invoke_with_raises(
    function: Callable[..., Any],
    expected: Union[type, Tuple[type, ...]],
    *args: Any,
    match: Optional[Union[str, Pattern[str]]] = None,
    **kwargs: Any,
) -> None:
    assert isinstance(expected, type)
    with pytest.raises(expected, match=match):
        function(*args, **kwargs)


def _invoke_with_warns(
    function: Callable[..., Any],
    expected: Union[type, Tuple[type, ...]],
    *args: Any,
    match: Optional[Union[str, Pattern[str]]] = None,
    **kwargs: Any,
) -> Any:
    assert isinstance(expected, type) or (isinstance(expected, tuple) and all(isinstance(e, type) for e in expected))
    with pytest.warns(expected, match=match):
        return function(*args, **kwargs)


def expect_error(
    function: Callable[..., Any],
    expected: Any,
    *args: Any,
    match: Optional[Union[str, Pattern[str]]] = None,
    **kwargs: Any,
) -> bool:
    if inspect.isclass(expected) and issubclass(expected, BaseException):
        _invoke_with_raises(function, expected, *args, match=match, **kwargs)
        return True

    if isinstance(expected, tuple):
        errors = tuple(filter(lambda e: inspect.isclass(e) and issubclass(e, BaseException), expected))
        if errors:
            _invoke_with_raises(function, errors, *args, match=match, **kwargs)
        return True

    return False


def expect_warning(
    function: Callable[..., Any],
    expected: Any,
    *args: Any,
    match: Optional[Union[str, Pattern[str]]] = None,
    **kwargs: Any,
) -> Any:
    if inspect.isclass(expected) and issubclass(expected, Warning):
        return _invoke_with_warns(function, expected, *args, match=match, **kwargs)

    if isinstance(expected, tuple):
        warnings = tuple(filter(lambda e: inspect.isclass(e) and issubclass(e, Warning), expected))
        if warnings:
            return _invoke_with_warns(function, warnings, *args, match=match, **kwargs)

    return function(*args, **kwargs)
