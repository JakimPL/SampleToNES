from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

from typehints import SerializedData

T = TypeVar("T")


def file_dialog_handler(func: Callable[[T, Path], None]) -> Callable[[T, int, SerializedData], None]:
    @wraps(func)
    def wrapper(self: T, sender: int, app_data: SerializedData) -> None:
        if not app_data or "file_path_name" not in app_data:
            return

        filepath = app_data["file_path_name"]
        if not filepath:
            return

        filepath = Path(filepath)
        func(self, filepath)

    return wrapper
