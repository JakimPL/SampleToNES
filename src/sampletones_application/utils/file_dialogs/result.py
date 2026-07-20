from functools import wraps
from pathlib import Path
from typing import Callable, Concatenate, Optional, ParamSpec, TypeVar, Union, cast, overload

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")


@overload
def ignore_none_path(
    func: Callable[Concatenate[T, Path, P], None],
) -> Callable[Concatenate[T, Optional[Path], P], None]: ...


@overload
def ignore_none_path(
    *,
    default: R,
) -> Callable[
    [Callable[Concatenate[T, Path, P], R]],
    Callable[Concatenate[T, Optional[Path], P], R],
]: ...


def ignore_none_path(
    func: Optional[Callable[Concatenate[T, Path, P], R]] = None,
    *,
    default: Optional[R] = None,
) -> Union[
    Callable[Concatenate[T, Optional[Path], P], R],
    Callable[
        [Callable[Concatenate[T, Path, P], R]],
        Callable[Concatenate[T, Optional[Path], P], R],
    ],
]:
    """Wraps a path handler so a cancelled dialog resolves to ``default``.

    Applied bare (``@ignore_none_path``) the wrapped method runs with the selected ``Path`` and
    yields ``None`` when the dialog was cancelled. Applied with a ``default``
    (``@ignore_none_path(default=...)``) the cancelled case yields that value instead, so a handler
    that reports an outcome — such as a save returning whether it wrote — carries a truthful result
    through the cancellation. Each handler body runs only with a real path.
    """

    def decorate(
        inner: Callable[Concatenate[T, Path, P], R],
    ) -> Callable[Concatenate[T, Optional[Path], P], R]:
        @wraps(inner)
        def wrapper(
            self: T,
            filepath: Optional[Path],
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            if filepath is None:
                return cast(R, default)

            return inner(self, filepath, *args, **kwargs)

        return cast(Callable[Concatenate[T, Optional[Path], P], R], wrapper)

    if func is not None:
        return decorate(func)

    return decorate
