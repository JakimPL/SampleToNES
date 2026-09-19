from typing import Final, List, Protocol

import dearpygui.dearpygui as dpg

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_shared.types.callback import StringCallback

CLIPBOARD_ANSWER_SECONDS: Final[float] = 1.0


class SelectionReader(Protocol):
    """Reads the clipboard's text, waiting ``seconds`` at most for the application holding it."""

    def read_text(self, seconds: float) -> str: ...


class X11TextClipboard:
    """The desktop's clipboard on X11: written through DearPyGui, read over a connection of its own.

    DearPyGui reads the clipboard through GLFW, which waits for the application holding it for as
    long as that application takes, holding DearPyGui's lock and the interpreter meanwhile; an owner
    that stays silent stops every frame for good. This clipboard reads on a worker instead, giving
    the owner ``CLIPBOARD_ANSWER_SECONDS`` to hand its text over, and an owner silent past that
    reads as holding no text. The frames keep being drawn meanwhile, which is also what lets this
    application's own window answer: GLFW hands over the text it holds as a frame polls its events.

    The answer reaches the render thread through ``CallbackQueue``, so the shutdown that stops the
    queue drops an answer still on its way, and the worker joins at teardown like any other. Reads
    asked while one is out wait for its answer, so a burst of them shares one transfer.
    """

    def __init__(self, reader: SelectionReader) -> None:
        self._reader = reader
        self._executor = SingleThreadExecutor()
        self._waiting: List[StringCallback] = []

    def read(self, on_text: StringCallback) -> None:
        self._waiting.append(on_text)
        if len(self._waiting) == 1:
            self._executor.execute(self._transfer, wait=True)

    def write(self, text: str) -> None:
        dpg.set_clipboard_text(text)

    def _transfer(self) -> None:
        """Reads on the worker and hands the text to the render thread, an empty one if the read fails.

        The reads waiting on this transfer hear from it whichever way it ends, so the next read
        starts a transfer of its own, and a failure still reaches the thread's own report.
        """
        text = ""
        try:
            text = self._reader.read_text(CLIPBOARD_ANSWER_SECONDS)
        finally:
            CallbackQueue.add(self._answer, text)

    def _answer(self, text: str) -> None:
        waiting, self._waiting = self._waiting, []
        for on_text in waiting:
            on_text(text)
