import inspect
from re import Pattern
from typing import Any, Callable, Final, Optional, Tuple, Type, Union

import pytest

# Opening a directory for reading raises IsADirectoryError on POSIX and PermissionError on Windows.
DIRECTORY_READ_ERRORS: Final[Tuple[Type[OSError], ...]] = (IsADirectoryError, PermissionError)


def _invoke_with_raises(
    function: Callable[..., Any],
    expected: Union[type, Tuple[type, ...]],
    *args: Any,
    match: Optional[Union[str, Pattern[str]]] = None,
    **kwargs: Any,
) -> None:
    assert isinstance(expected, type) or (isinstance(expected, tuple) and all(isinstance(e, type) for e in expected))
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
        all_errors = all(inspect.isclass(e) and issubclass(e, BaseException) for e in expected)
        any_error = any(inspect.isclass(e) and issubclass(e, BaseException) for e in expected)
        if all_errors and any_error:
            _invoke_with_raises(function, expected, *args, match=match, **kwargs)
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
        all_warnings = all(inspect.isclass(e) and issubclass(e, Warning) for e in expected)
        any_warning = any(inspect.isclass(e) and issubclass(e, Warning) for e in expected)
        if all_warnings and any_warning:
            return _invoke_with_warns(function, expected, *args, match=match, **kwargs)

    return function(*args, **kwargs)
