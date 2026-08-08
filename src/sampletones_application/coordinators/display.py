import math
from typing import Optional

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.layout.behavior.display import DisplayBehavior
from sampletones_application.layout.general.window import WindowLayout
from sampletones_application.tags.settings import TAG_SETTINGS_DISPLAY_DIALOG_DISCARD
from sampletones_application.ui.panels.dialogs.countdown import GUICountdownWindow
from sampletones_application.ui.panels.dialogs.display_settings import (
    GUIDisplaySettingsWindow,
)
from sampletones_application.utils.frame_limiter import FrameLimiter
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.shared.display_settings import (
    DisplaySettings,
    DisplaySettingsViewModel,
    WindowMode,
)
from sampletones_application.viewport import ViewportManager
from sampletones_shared.display import Resolution


class DisplayCoordinator:
    """Owns the display settings: the options offered, the live application of a change, and the
    countdown that returns a window mode nobody confirmed.

    A change reaches the screen the moment it is made, so a user judges it by looking at it, while
    the session keeps the values the dialog opened with until OK commits them. Cancel re-applies
    that snapshot, asking first when there is something to lose.

    Changing the window's size, its frame, or fullscreen can leave the window unreadable, so each
    of those arms a countdown over the dialog: keeping it disarms the clock and leaves the change
    pending, and letting the clock run out brings the last confirmed window mode back while every
    other pending edit stays.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        viewport_manager: ViewportManager,
        frame_limiter: FrameLimiter,
        palette_source: PaletteSource,
        palette_catalog: PaletteCatalog,
        *,
        window: GUIDisplaySettingsWindow,
        countdown: GUICountdownWindow,
        behavior: DisplayBehavior,
        window_layout: WindowLayout,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._session_manager = session_manager
        self._viewport_manager = viewport_manager
        self._frame_limiter = frame_limiter
        self._palette_source = palette_source
        self._palette_catalog = palette_catalog
        self._window = window
        self._countdown = countdown
        self._behavior = behavior
        self._window_layout = window_layout
        self._dialogs = dialogs
        self._language_manager = language_manager

        self._settings: Optional[DisplaySettings] = None
        self._snapshot: Optional[DisplaySettings] = None
        self._armed: Optional[WindowMode] = None
        self._remaining: float = 0.0

        self._window.on_settings_changed = self._change
        self._window.on_commit = self._commit
        self._window.on_cancel = self._request_close
        self._countdown.on_keep = self._keep
        self._countdown.on_revert = self._revert

    def open(self) -> None:
        """Shows the dialog seeded with the settings in force, snapshotting them for a cancel.

        A window sitting at a size of its own selects the offered one nearest it, and that
        selection becomes the state being edited, so what the dialog shows is what it applies.
        """
        view_model = self._view_model(self._settings_in_force())
        self._snapshot = view_model.settings
        self._settings = view_model.settings
        self._window.open(view_model)

    def tick(self, delta_time: float) -> None:
        """Advances an armed countdown, restoring the last confirmed window mode when it runs out."""
        if self._armed is None:
            return

        self._remaining -= delta_time
        if self._remaining <= 0.0:
            self._revert()
            return

        self._countdown.set_remaining(self._displayed_seconds())

    def _change(self, settings: DisplaySettings) -> None:
        """Puts an edit on screen, arming the countdown when it changed the window mode."""
        previous = self._require_settings()
        self._settings = settings
        self._apply(previous, settings)
        if settings.window != previous.window:
            self._arm(previous.window)

        self._window.update_view(self._view_model(settings))

    def _arm(self, restorable: WindowMode) -> None:
        """Starts the countdown that brings ``restorable`` back unless the change is confirmed.

        A countdown already running keeps the mode it was going to restore and starts its count
        again, so a run of unconfirmed changes still returns to the mode last seen as readable.
        """
        if self._armed is None:
            self._armed = restorable

        self._remaining = self._behavior.revert_countdown_seconds
        self._countdown.open(self._displayed_seconds())

    def _disarm(self) -> None:
        self._armed = None
        self._remaining = 0.0
        self._countdown.hide()

    def _keep(self) -> None:
        """Accepts the window mode on screen, which stays pending until OK commits it."""
        self._disarm()

    def _revert(self) -> None:
        """Brings the last confirmed window mode back, leaving every other pending edit in place."""
        restorable = self._armed
        self._disarm()
        if restorable is None:
            return

        self._restore(self._require_settings().with_window(restorable))

    def _restore(self, settings: DisplaySettings) -> None:
        """Puts ``settings`` on screen as the state in force, without arming a countdown."""
        previous = self._require_settings()
        self._settings = settings
        self._apply(previous, settings)
        self._window.update_view(self._view_model(settings))

    def _commit(self) -> None:
        """Writes the state on screen to the session and closes the dialog."""
        settings = self._require_settings()
        self._disarm()
        self._session_manager.set_palette_name(settings.palette)
        self._session_manager.set_vsync(settings.vsync)
        self._session_manager.set_max_fps(settings.frame_rate)
        self._session_manager.set_borderless(settings.window.borderless)
        self._close()

    def _request_close(self) -> None:
        """Answers Cancel, Escape and the title bar's close button, asking before losing an edit."""
        if self._require_settings() == self._snapshot:
            self._discard()
            return

        self._window.reveal()
        self._dialogs.show_confirmation(
            tag=TAG_SETTINGS_DISPLAY_DIALOG_DISCARD,
            title=self._language_manager["settings.display.title.discard_confirmation"],
            message=self._language_manager["settings.display.message.discard_confirmation"],
            on_confirm=self._discard,
            ok_label=self._language_manager["settings.display.label.discard_button"],
            cancel_label=self._language_manager["settings.display.label.keep_editing_button"],
        )

    def _discard(self) -> None:
        """Puts back the settings the dialog opened with and closes it."""
        self._disarm()
        snapshot = self._snapshot
        if snapshot is not None:
            self._apply(self._require_settings(), snapshot)

        self._close()

    def _close(self) -> None:
        self._settings = None
        self._snapshot = None
        self._window.hide()

    def _apply(self, previous: DisplaySettings, current: DisplaySettings) -> None:
        """Puts every setting that differs on screen, leaving the session untouched."""
        if current.palette != previous.palette:
            self._palette_source.activate(self._palette_catalog.select(current.palette))

        if current.vsync != previous.vsync:
            self._viewport_manager.set_vsync(current.vsync)

        if current.frame_rate != previous.frame_rate:
            self._frame_limiter.set_max_fps(current.frame_rate)

        self._apply_window(previous.window, current.window)

    def _apply_window(self, previous: WindowMode, current: WindowMode) -> None:
        """Puts the window mode on screen, fullscreen first so a size lands on a windowed viewport.

        Fullscreen goes through the viewport manager's own toggle, which is the path the View menu
        and F11 take, so the menu's checkmark follows a change made here.
        """
        if current.fullscreen != previous.fullscreen:
            self._viewport_manager.toggle_fullscreen()

        if current.borderless != previous.borderless:
            self._viewport_manager.set_borderless(current.borderless)

        if current.resolution != previous.resolution:
            self._viewport_manager.set_resolution(
                current.resolution.width,
                current.resolution.height,
            )

    def _settings_in_force(self) -> DisplaySettings:
        """The display state the application is running under right now."""
        width, height = self._viewport_manager.resolution
        return DisplaySettings(
            palette=self._palette_source.palette.name,
            window=WindowMode(
                resolution=Resolution(width=width, height=height),
                borderless=self._session_manager.borderless,
                fullscreen=self._session_manager.fullscreen,
            ),
            vsync=self._session_manager.vsync,
            frame_rate=self._session_manager.max_fps,
        )

    def _view_model(self, settings: DisplaySettings) -> DisplaySettingsViewModel:
        """The dialog's view of ``settings``, offering the sizes its monitor leaves room for."""
        area = self._viewport_manager.monitor_area
        return DisplaySettingsViewModel.build(
            settings,
            resolutions=self._behavior.resolutions,
            frame_rates=self._behavior.frame_rates,
            palettes=self._palette_catalog.names,
            min_width=self._window_layout.min_width,
            min_height=self._window_layout.min_height,
            max_width=area.usable_width,
            max_height=area.usable_height,
        )

    def _displayed_seconds(self) -> int:
        """The whole seconds the prompt shows, rounded up so the last one reads as one."""
        return math.ceil(self._remaining)

    def _require_settings(self) -> DisplaySettings:
        """The state the open dialog is editing.

        Raises:
            SystemError: when the dialog is driven while closed.
        """
        if self._settings is None:
            raise SystemError("The display settings are edited only while the dialog is open")

        return self._settings
