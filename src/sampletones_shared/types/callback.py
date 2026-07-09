from pathlib import Path
from typing import Any, Callable, TypeVar

Callback = Callable[..., Any]
VoidCallback = Callable[[], None]
PathCallback = Callable[[Path], None]
StringCallback = Callable[[str], None]
MessageCallback = Callable[..., str]
CallbackT = TypeVar("CallbackT", bound=Callback)
