from typing import Any, List, Union

from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_shared.types.callback import MessageCallback


class RecordedStatusBar(GUIStatusBar):
    """A status bar keeping every message it is given, with no window or theme to draw them with.

    A test reading what a hover or a gesture says reads the messages, in the order they were set.
    """

    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        self.messages: List[str] = []

    def set(
        self,
        message_or_function: Union[str, MessageCallback],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.messages.append(self.get_message(message_or_function, *args, **kwargs))
