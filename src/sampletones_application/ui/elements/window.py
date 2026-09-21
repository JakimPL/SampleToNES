from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.layout.primitives import DialogGeometry
from sampletones_application.tags.general import TAG_GLOBAL_THEME_DIALOG_WINDOW
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import center_when_settled, viewport_center
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_delete_item
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.placement import centered_position
from sampletones_shared.types.callback import VoidCallback


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
    the two from competing for the one modal DearPyGui carries at a time. The
    position a window was placed at is its own from then on, so the return brings
    it back where it stood.

    A window claims the screen while it stands, so the reader answers it before going on. One
    reporting work already under way clears ``_claims_the_screen`` instead, which leaves the rest
    of the interface live beside it.
    """

    _claims_the_screen: bool = True

    def __init__(self, tag: str, geometry: DialogGeometry) -> None:
        self._geometry = geometry
        super().__init__(tag, geometry.width, geometry.minimum_size[1])

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

        The window opens at the size its geometry states and grows in height to hold more than
        that, so a prompt whose text wraps over several lines and a form that unfolds a group
        after opening both show the whole of what they hold. Its width is the one its geometry
        states, held as the largest the window may take as well as the smallest, so an item
        stretching across the window measures against a width that stands.

        A dialog offers the title bar's close button when ``on_close`` names what closing means,
        and omits it otherwise, so the only way out of a window is one the window answers for.
        """
        with dpg.window(
            tag=self.tag,
            label=label,
            width=self._geometry.width,
            min_size=list(self._geometry.minimum_size),
            max_size=list(self._geometry.maximum_size),
            autosize=True,
            no_resize=True,
            no_collapse=True,
            no_close=on_close is None,
            on_close=on_close,
            modal=self._claims_the_screen,
        ):
            yield

    def show(self, *args: Any, **kwargs: Any) -> None:
        """Builds this appearance's tree, places it, and holds it centered as it takes its size.

        A window stating a height is placed before it is ever drawn, so the first frame carrying
        it already shows it centered — which is what keeps it clear of the spot DearPyGui opens
        an unplaced modal at. A window whose height its content settles has none to place from
        and is centered on the frame that settles it. The drawn size is known only after a frame
        has carried it, so the correction waits for those frames to arrive on their own: waiting
        for one in place would hold the render thread, and a window is raised from wherever a
        result reaches the screen — including the callback drain that runs between frames, where
        the frame being waited for is the one this call stands in the way of.
        """
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_window()
        ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG_WINDOW).bind_to_item(self.tag)
        if self._geometry.height is not None:
            dpg.set_item_pos(self.tag, list(centered_position(viewport_center(), *self._geometry.minimum_size)))

        center_when_settled(self.tag)

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
