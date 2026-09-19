from typing import Callable, Optional, Protocol

ClipboardTextCallback = Callable[[Optional[str]], None]


class TextClipboard(Protocol):
    """The clipboard the desktop shares between applications, as text going out and coming back.

    The application holding the clipboard hands its text over in its own time, so a read names what
    receives the text once it has arrived. The selector in ``selection`` picks the implementation
    that fits the running environment.
    """

    def read(self, on_text: ClipboardTextCallback) -> None:
        """Hands the text standing on the clipboard to ``on_text``, on the render thread.

        A read is asked for on the render thread, where every gesture reaching the clipboard runs.
        An application that gives no answer leaves ``on_text`` with ``None``, which stands apart
        from the empty text a clipboard holding nothing reads as.
        """

    def write(self, text: str) -> None: ...
