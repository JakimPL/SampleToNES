from pathlib import Path
from typing import Any, Callable, Tuple, TypeVar

Callback = Callable[..., Any]
VoidCallback = Callable[[], None]
PathCallback = Callable[[Path], None]
PathsCallback = Callable[[Tuple[Path, ...]], None]
StringCallback = Callable[[str], None]
MessageCallback = Callable[..., str]
CallbackT = TypeVar("CallbackT", bound=Callback)
QueryT = TypeVar("QueryT")
