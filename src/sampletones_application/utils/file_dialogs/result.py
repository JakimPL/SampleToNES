from functools import wraps
from pathlib import Path
from typing import Callable, Concatenate, ParamSpec, TypeVar, cast

P = ParamSpec("P")
T = TypeVar("T")


def ignore_none_path(
    func: Callable[Concatenate[T, Path, P], None],
) -> Callable[Concatenate[T, Path | None, P], None]:
    """
    Wraps a path handler so a cancelled dialog is a no-op.

    The wrapped method runs with the selected ``Path`` when the dialog returned one,
    and returns early when the result is ``None``, so each handler body can assume it
    always has a real path.
    """

    @wraps(func)
    def wrapper(
        self: T,
        filepath: Path | None,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if filepath is None:
            return

        func(self, filepath, *args, **kwargs)

    return cast(
        Callable[Concatenate[T, Path | None, P], None],
        wrapper,
    )
