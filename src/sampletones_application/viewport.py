import sys
from typing import Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.layout.general.window import WindowLayout
from sampletones_application.ui.resources.items import IconResource
from sampletones_application.ui.resources.resources import get_icon_path
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.monitors import monitor_area_for_window
from sampletones_shared.application import SAMPLETONES_NAME
from sampletones_shared.types.callback import VoidCallback


class ViewportManager:
    def __init__(
        self,
        session_manager: SessionManager,
        theme: Theme,
        window: WindowLayout,
        *,
        on_fullscreen_state_changed: VoidCallback,
    ) -> None:
        self._session_manager = session_manager
        self._theme = theme
        self._window = window
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
            min_width=self._window.min_width,
            min_height=self._window.min_height,
            small_icon=str(icon_file_path),
            large_icon=str(icon_file_path),
            x_pos=window_x,
            y_pos=window_y,
            decorated=not self._session_manager.borderless,
            disable_close=True,
            vsync=self._session_manager.vsync,
        )

        self.refresh_clear_color()

    def set_resolution(self, width: int, height: int) -> None:
        """Resizes the window, holding it at the configured minimum."""
        dpg.set_viewport_width(max(self._window.min_width, width))
        dpg.set_viewport_height(max(self._window.min_height, height))

    def set_borderless(self, borderless: bool) -> None:
        """Shows or hides the system's title bar and frame around the window."""
        dpg.set_viewport_decorated(not borderless)

    def set_vsync(self, vsync: bool) -> None:
        """Sets whether the render loop waits for the monitor's refresh."""
        dpg.set_viewport_vsync(vsync)

    @property
    def resolution(self) -> Tuple[int, int]:
        """The size the window is showing at right now."""
        return dpg.get_viewport_width(), dpg.get_viewport_height()

    def refresh_clear_color(self) -> None:
        """Paints the area around the windows in the main theme's background colour.

        DearPyGui holds the clear colour outside the theme system, so it is issued again
        whenever the theme's background answers with a new value.
        """
        color = self._theme.get_color(dpg.mvAll, dpg.mvThemeCol_WindowBg)
        assert color is not None, "Background color is not defined in the main theme"
        dpg.set_viewport_clear_color(list(color))

    def update_title(self, title: str) -> None:
        """Shows an already composed title on the window, keeping title wording with its owner."""
        dpg.set_viewport_title(title)

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

    def _fit_window_to_monitor(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Tuple[int, int, int, int]:
        """Fit the window to its monitor, hold it at the configured minimum, and clamp it within reserved margins.

        The size is limited to the monitor's usable area so the title bar and side panels stay on
        screen once the decoration frame is added, and held at ``min_width`` / ``min_height`` so
        even a small requested size opens usably wide. The position is nudged inside the resulting
        margins so every edge lands within the monitor.
        """
        area = monitor_area_for_window(
            x,
            y,
            width,
            height,
            usable_ratio=self._window.max_monitor_ratio,
            fallback_monitor=self._window.fallback_monitor,
        )
        fitted_width = max(self._window.min_width, min(width, area.usable_width))
        fitted_height = max(self._window.min_height, min(height, area.usable_height))

        margin_x = (area.width - area.usable_width) // 2
        margin_y = (area.height - area.usable_height) // 2
        fitted_x = max(
            area.x + margin_x,
            min(x, area.x + area.width - margin_x - fitted_width),
        )
        fitted_y = max(
            area.y + margin_y,
            min(y, area.y + area.height - margin_y - fitted_height),
        )

        return fitted_x, fitted_y, fitted_width, fitted_height
