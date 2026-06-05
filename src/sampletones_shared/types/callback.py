from pathlib import Path
from typing import Any, Callable, TypeVar

Callback = Callable[..., Any]
VoidCallback = Callable[[], None]
PathCallback = Callable[[Path], None]
MessageCallback = Callable[..., str]
CallbackT = TypeVar("CallbackT", bound=Callback)
