import sys
import tkinter
from typing import List, Optional, Tuple

import dearpygui.dearpygui as dpg
from screeninfo import Monitor, get_monitors

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.resources.items import IconResource
from sampletones_application.ui.resources.resources import get_icon_path
from sampletones_application.ui.themes.default import DefaultTheme
from sampletones_shared.types.callback import VoidCallback


class ViewportManager:
    def __init__(
        self,
        session_manager: SessionManager,
        theme: DefaultTheme,
        *,
        layout: GeneralLayout,
        on_fullscreen_state_changed: VoidCallback,
    ) -> None:
        self._session_manager = session_manager
        self._theme = theme
        self._layout = layout
        self._on_fullscreen_state_changed = on_fullscreen_state_changed

    def create_viewport(self) -> None:
        if sys.platform.startswith("win"):
            icon_filename = IconResource.WIN
        else:
            icon_filename = IconResource.UNIX

        icon_file_path = get_icon_path(icon_filename)

        dpg.create_viewport(
            title="SampleToNES",
            width=self._layout.window.width,
            height=self._layout.window.height,
            small_icon=str(icon_file_path),
            large_icon=str(icon_file_path),
            x_pos=self._session_manager.window_x,
            y_pos=self._session_manager.window_y,
            decorated=not self._session_manager.fullscreen,
            disable_close=True,
        )

        if self._session_manager.fullscreen:
            self.enable_fullscreen()
        else:
            self.disable_fullscreen()

        color = self._theme.get_color(dpg.mvAll, dpg.mvThemeCol_WindowBg)
        assert color is not None, "Background color is not defined in the main theme"
        dpg.set_viewport_clear_color(list(color))

    def update_title(self, app_name: str, document: str) -> None:
        if document:
            dpg.set_viewport_title(f"{app_name} — {document}")
        else:
            dpg.set_viewport_title(app_name)

    def enable_fullscreen(self) -> None:
        dpg.set_viewport_decorated(False)

        window_x = self._session_manager.window_x
        window_y = self._session_manager.window_y
        window_width: Optional[int] = None
        window_height: Optional[int] = None

        monitor = self._monitor_for_position(window_x, window_y)
        if monitor is not None:
            window_x = int(monitor.x)
            window_y = int(monitor.y)
            window_width = int(monitor.width)
            window_height = int(monitor.height)
        else:
            screen_dimensions = self._get_screen_dimensions()
            window_width = screen_dimensions[0]
            window_height = screen_dimensions[1]

        self._apply_window_state(
            fullscreen=True,
            x=window_x,
            y=window_y,
            width=window_width,
            height=window_height,
        )

    def disable_fullscreen(self) -> None:
        window_width = self._session_manager.window_width
        window_height = self._session_manager.window_height
        window_x = self._session_manager.window_x
        window_y = self._session_manager.window_y

        monitor = self._monitor_for_position(window_x, window_y)
        if monitor is not None:
            screen_x = int(monitor.x)
            screen_y = int(monitor.y)
            screen_w = int(monitor.width)
            screen_h = int(monitor.height)

            window_width = min(window_width, screen_w)
            window_height = min(window_height, screen_h)

            window_x = max(
                0,
                screen_x,
                min(window_x, screen_x + screen_w - window_width),
            )
            window_y = max(
                0,
                screen_y,
                min(window_y, screen_y + screen_h - window_height),
            )
        else:
            window_x = max(0, window_x)
            window_y = max(0, window_y)

        self._apply_window_state(
            fullscreen=False,
            x=window_x,
            y=window_y,
            width=window_width,
            height=window_height,
        )

        dpg.set_viewport_decorated(True)

    def toggle_fullscreen(self) -> None:
        if not self._session_manager.fullscreen:
            self.enable_fullscreen()
        else:
            self.disable_fullscreen()

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

    def _apply_window_state(
        self,
        fullscreen: bool,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        dpg.set_viewport_pos([x, y])
        dpg.set_viewport_width(width)
        dpg.set_viewport_height(height)

        self._session_manager.set_window_state(
            fullscreen=fullscreen,
            x=x,
            y=y,
            width=width,
            height=height,
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

    def _monitor_for_position(self, x: float, y: float) -> Optional[Monitor]:
        monitors = self._get_monitors()
        position_x = float(x)
        position_y = float(y)

        for monitor in monitors:
            if all(
                (
                    monitor.x <= position_x < (monitor.x + monitor.width),
                    monitor.y <= position_y < (monitor.y + monitor.height),
                )
            ):
                return monitor

        return monitors[0] if monitors else None
