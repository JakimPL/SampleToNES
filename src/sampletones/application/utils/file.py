from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

from sampletones.typehints import Sender, SerializedData
from sampletones.utils import to_path

T = TypeVar("T")


def file_dialog_handler(func: Callable[[T, Path], None]) -> Callable[[T, int, SerializedData], None]:
    @wraps(func)
    def wrapper(self: T, sender: Sender, app_data: SerializedData) -> None:
        if not app_data or "file_path_name" not in app_data:
            return

        filepath = app_data["file_path_name"]
        if not filepath:
            return

        filepath = to_path(filepath)
        func(self, filepath)

    return wrapper
