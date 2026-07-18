import sys
import tkinter
from typing import Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg
from screeninfo import Monitor, get_monitors

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.ui.resources.items import IconResource
from sampletones_application.ui.resources.resources import get_icon_path
from sampletones_application.ui.themes.theme import Theme
from sampletones_shared.application import SAMPLETONES_NAME
from sampletones_shared.types.callback import VoidCallback

_MAX_WINDOW_MONITOR_RATIO: Final[float] = 0.9


class ViewportManager:
    def __init__(
        self,
        session_manager: SessionManager,
        theme: Theme,
        *,
        min_width: int,
        min_height: int,
        on_fullscreen_state_changed: VoidCallback,
    ) -> None:
        self._session_manager = session_manager
        self._theme = theme
        self._min_width = min_width
        self._min_height = min_height
        self._on_fullscreen_state_changed = on_fullscreen_state_changed

    def create_viewport(self) -> None:
        if sys.platform.startswith("win"):
            icon_filename = IconResource.WIN
        else:
            icon_filename = IconResource.UNIX

        icon_file_path = get_icon_path(icon_filename)

        window_x, window_y, window_width, window_height = self._fit_window_to_monitor(
            self._session_manager.window_x,
            self._session_manager.window_y,
            self._session_manager.window_width,
            self._session_manager.window_height,
        )

        dpg.create_viewport(
            title=SAMPLETONES_NAME,
            width=window_width,
            height=window_height,
            min_width=self._min_width,
            min_height=self._min_height,
            small_icon=str(icon_file_path),
            large_icon=str(icon_file_path),
            x_pos=window_x,
            y_pos=window_y,
            decorated=True,
            disable_close=True,
        )

        color = self._theme.get_color(dpg.mvAll, dpg.mvThemeCol_WindowBg)
        assert color is not None, "Background color is not defined in the main theme"
        dpg.set_viewport_clear_color(list(color))

    def update_title(self, app_name: str, document: str) -> None:
        if document:
            dpg.set_viewport_title(f"{app_name} — {document}")
        else:
            dpg.set_viewport_title(app_name)

    def apply_fullscreen_state(self) -> None:
        """Enters fullscreen once the viewport is live when the session requests it.

        A DPG viewport always starts windowed, so the persisted preference is reached with a
        single toggle after the window exists, which also keeps the session state authoritative.
        """
        if self._session_manager.fullscreen:
            dpg.toggle_viewport_fullscreen()

    def toggle_fullscreen(self) -> None:
        dpg.toggle_viewport_fullscreen()
        self._persist_fullscreen(not self._session_manager.fullscreen)

    def save_window_state(self) -> None:
        if self._session_manager.fullscreen:
            return

        viewport_x, viewport_y = dpg.get_viewport_pos()
        self._session_manager.set_window_state(
            fullscreen=False,
            x=int(viewport_x),
            y=int(viewport_y),
            width=dpg.get_viewport_width(),
            height=dpg.get_viewport_height(),
        )

    def _persist_fullscreen(self, fullscreen: bool) -> None:
        self._session_manager.set_window_state(
            fullscreen=fullscreen,
            x=self._session_manager.window_x,
            y=self._session_manager.window_y,
            width=self._session_manager.window_width,
            height=self._session_manager.window_height,
        )
        self._on_fullscreen_state_changed()

    @staticmethod
    def _get_screen_dimensions() -> Tuple[int, int]:
        _root = tkinter.Tk()
        _root.withdraw()
        window_width = int(_root.winfo_screenwidth())
        window_height = int(_root.winfo_screenheight())
        _root.destroy()
        return window_width, window_height

    @staticmethod
    def _get_monitors() -> List[Monitor]:
        return get_monitors()

    def _fit_window_to_monitor(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Tuple[int, int, int, int]:
        """Fit the window to its monitor, hold it at the configured minimum, and clamp it within reserved margins.

        The size is limited to ``_MAX_WINDOW_MONITOR_RATIO`` of the monitor so the title bar and
        side panels stay on screen once the decoration frame is added, and held at ``min_width`` /
        ``min_height`` so a window persisted from an earlier session still opens usably wide. The
        position is nudged inside the resulting margins so every edge lands within the monitor.
        """
        monitor = self._monitor_for_window(x, y, width, height)
        if monitor is not None:
            screen_x = int(monitor.x)
            screen_y = int(monitor.y)
            screen_w = int(monitor.width)
            screen_h = int(monitor.height)
        else:
            screen_x = 0
            screen_y = 0
            screen_w, screen_h = self._get_screen_dimensions()

        usable_w = int(screen_w * _MAX_WINDOW_MONITOR_RATIO)
        usable_h = int(screen_h * _MAX_WINDOW_MONITOR_RATIO)
        fitted_width = max(self._min_width, min(width, usable_w))
        fitted_height = max(self._min_height, min(height, usable_h))

        margin_x = (screen_w - usable_w) // 2
        margin_y = (screen_h - usable_h) // 2
        fitted_x = max(screen_x + margin_x, min(x, screen_x + screen_w - margin_x - fitted_width))
        fitted_y = max(screen_y + margin_y, min(y, screen_y + screen_h - margin_y - fitted_height))

        return fitted_x, fitted_y, fitted_width, fitted_height

    def _monitor_for_window(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Optional[Monitor]:
        monitors = self._get_monitors()
        if not monitors:
            return None

        best_monitor = monitors[0]
        best_overlap = -1
        for monitor in monitors:
            overlap_width = max(
                0,
                min(x + width, monitor.x + monitor.width) - max(x, monitor.x),
            )
            overlap_height = max(
                0,
                min(y + height, monitor.y + monitor.height) - max(y, monitor.y),
            )
            overlap = overlap_width * overlap_height
            if overlap > best_overlap:
                best_overlap = overlap
                best_monitor = monitor

        return best_monitor
