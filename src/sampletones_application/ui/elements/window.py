from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_THEME_DIALOG_WINDOW
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import center_item, center_when_settled
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_delete_item
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.types.data import SerializedData


class GUIWindow(GUIPanel, ABC):
    """
    A ``GUIPanel`` whose widget tree is rebuilt on each appearance.

    Unlike a standard panel, it is fully deleted from DPG when hidden and
    recreated when shown — appropriate when content depends on runtime context.
    The ``prepare`` step captures arguments before the previous tree is torn
    down. Each rebuild binds the elevated dialog-window theme so the window
    floats above the app with an accent border and title bar.

    A dialog that raises another modal — a prompt, a countdown — hands the screen
    over with ``yield_to`` and takes it back with ``resume``, which is what keeps
    the two from competing for the one modal DearPyGui carries at a time.

    A window holding prose of a length it learns at the moment it opens sets
    ``_fits_content``, which lets it grow past the height it states.
    """

    _fits_content: bool = False

    def center(self) -> None:
        center_item(self.tag)

    def yield_to(self, raise_modal: VoidCallback) -> None:
        """Steps off screen and runs ``raise_modal`` a frame later, so what it raises can open.

        DearPyGui carries one modal at a time: a modal built while another one is still on
        screen opens as a hidden window nobody can reach. This window goes off screen first
        and the frame it was drawn in finishes, leaving the new modal alone on screen. The
        widget tree stays where it is, so whatever is being edited here survives the visit
        and :meth:`resume` brings it back untouched.
        """
        dpg_configure_item(self.tag, show=False)
        FrameCallbackManager.set_frame_callback(raise_modal)

    def resume(self) -> None:
        """Comes back on screen once the modal this window yielded to is gone.

        The return waits a frame for the same reason the hand-off does: the modal being
        dismissed still holds the screen for the frame it is dismissed in.
        """
        FrameCallbackManager.set_frame_callback(lambda: dpg_configure_item(self.tag, show=True))

    @contextmanager
    def dialog_window(
        self,
        *,
        label: str,
        on_close: Optional[VoidCallback],
    ) -> Iterator[None]:
        """Open this window's modal frame, with the block's widgets building inside it.

        The window holds the width it states, which is what lets a field, a combo or a button
        stretch across it: a stretched item measures one pixel inside the region it is offered, so
        a window sized from its own content would take that pixel back on every frame. A stated
        width settles the geometry in one pass and gives every dialog the same reading width
        whatever it holds.

        A window that sets ``_fits_content`` reads its stated height as a floor and grows to hold
        what it is given, so a prompt whose text wraps over several lines shows all of it.

        A dialog offers the title bar's close button when ``on_close`` names what closing means,
        and omits it otherwise, so the only way out of a window is one the window answers for.
        """
        geometry: SerializedData = (
            {"min_size": (self.width, self.height), "autosize": True} if self._fits_content else {"height": self.height}
        )
        with dpg.window(
            tag=self.tag,
            label=label,
            width=self.width,
            no_resize=True,
            no_collapse=True,
            no_close=on_close is None,
            on_close=on_close,
            modal=True,
            **geometry,
        ):
            yield

    def show(self, *args: Any, **kwargs: Any) -> None:
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_window()
        ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG_WINDOW).bind_to_item(self.tag)
        if self._fits_content:
            center_when_settled(self.tag)
            return

        dpg.split_frame()
        self.center()

    def hide(self) -> None:
        self._teardown()
        dpg_delete_item(self.tag)

    def _teardown(self) -> None:
        """Releases resources tied to the current appearance before its tree is deleted.

        The base implementation is a no-op; a window that installs per-appearance handlers such
        as a keyboard navigator overrides this to dispose them, keeping setup and teardown
        symmetric across every reopen.
        """

    def create_panel(self, parent: str) -> None:
        """Satisfy the panel contract for a top-level window, which owns its own
        ``dpg.window`` and builds through ``create_window``."""
        self.create_window()

    @abstractmethod
    def create_window(self) -> None: ...

    @abstractmethod
    def prepare(self, *args: Any, **kwargs: Any) -> None: ...
