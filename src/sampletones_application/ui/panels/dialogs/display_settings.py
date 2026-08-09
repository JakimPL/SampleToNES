from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.tags.general import TAG_GLOBAL_THEME_DIALOG
from sampletones_application.tags.settings import (
    TAG_SETTINGS_DISPLAY_BUTTON_CANCEL,
    TAG_SETTINGS_DISPLAY_BUTTON_OK,
    TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS,
    TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN,
    TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC,
    TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE,
    TAG_SETTINGS_DISPLAY_COMBO_PALETTE,
    TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION,
    TAG_SETTINGS_DISPLAY_WINDOW,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.field import labeled_field, subheader
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import (
    DialogKeyboardNavigator,
    FocusStop,
)
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.shared.display_settings import (
    DisplaySettings,
    DisplaySettingsViewModel,
    WindowMode,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

SettingsCallback = Callable[[DisplaySettings], None]


class GUIDisplaySettingsWindow(GUIWindow):
    """Modal form over how the application presents itself: its window, its pacing and its theme.

    Every control reports the whole edited state through ``on_settings_changed`` the moment it
    changes, so the owner puts it on screen and the user judges the result by looking at it.
    ``on_commit`` states that the state on screen is the one to keep, and ``on_cancel`` that the
    dialog is done with — which the owner answers by restoring what it snapshotted.
    """

    def __init__(
        self,
        *,
        layout: SettingsLayout,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._language_manager = language_manager
        self._layout = layout
        self._router = key_router
        self._shortcuts = shortcut_source
        self._dialog_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG)
        self._navigator: Optional[DialogKeyboardNavigator] = None
        self._view_model: Optional[DisplaySettingsViewModel] = None

        self.on_settings_changed: Optional[SettingsCallback] = None
        self.on_commit: Optional[VoidCallback] = None
        self.on_cancel: Optional[VoidCallback] = None

        self._lbl_unlimited = language_manager["settings.display.label.unlimited_frame_rate"]

        super().__init__(
            tag=TAG_SETTINGS_DISPLAY_WINDOW,
            width=layout.display.window.width,
            height=layout.display.window.height,
        )

    def open(self, view_model: DisplaySettingsViewModel) -> None:
        """Shows the window seeded with the given display settings."""
        self._view_model = view_model
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The rendered values are seeded by :meth:`open` before the tree rebuilds."""

    def update_view(self, view_model: DisplaySettingsViewModel) -> None:
        """Re-seeds the controls of the open window from the given display settings."""
        self._view_model = view_model
        self._render()

    def create_window(self) -> None:
        with self.dialog_window(
            label=self._language_manager["settings.display.title.window_title"],
            on_close=self._request_cancel,
        ):
            self._create_window_section()
            dpg.add_separator()
            self._create_pacing_section()
            dpg.add_separator()
            self._create_appearance_section()
            dpg.add_separator()
            self._create_action_buttons()

        for combo_tag in (
            TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION,
            TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE,
            TAG_SETTINGS_DISPLAY_COMBO_PALETTE,
        ):
            self._dialog_theme.bind_to_item(combo_tag)

        self._render()
        self._install_navigation()

    def _create_window_section(self) -> None:
        view_model = self._require_view_model()
        subheader(self._language_manager["settings.display.title.section_window"])
        with labeled_field(
            self._language_manager["settings.display.label.resolution"],
            self._layout.label_width,
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION,
                items=list(view_model.resolution_items),
                default_value=view_model.current_resolution_item,
                width=self._layout.combo_width,
                callback=self._on_resolution_changed,
            )

        dpg.add_checkbox(
            tag=TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS,
            label=self._language_manager["settings.display.label.borderless"],
            default_value=view_model.settings.window.borderless,
            callback=self._on_borderless_changed,
        )
        dpg.add_checkbox(
            tag=TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN,
            label=self._language_manager["settings.display.label.fullscreen"],
            default_value=view_model.settings.window.fullscreen,
            callback=self._on_fullscreen_changed,
        )

    def _create_pacing_section(self) -> None:
        view_model = self._require_view_model()
        subheader(self._language_manager["settings.display.title.section_pacing"])
        dpg.add_checkbox(
            tag=TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC,
            label=self._language_manager["settings.display.label.vsync"],
            default_value=view_model.settings.vsync,
            callback=self._on_vsync_changed,
        )
        with labeled_field(
            self._language_manager["settings.display.label.frame_rate"],
            self._layout.label_width,
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE,
                items=list(view_model.frame_rate_items(self._lbl_unlimited)),
                default_value=view_model.current_frame_rate_item(self._lbl_unlimited),
                width=self._layout.combo_width,
                callback=self._on_frame_rate_changed,
            )

    def _create_appearance_section(self) -> None:
        view_model = self._require_view_model()
        subheader(self._language_manager["settings.display.title.section_appearance"])
        with labeled_field(
            self._language_manager["settings.display.label.theme"],
            self._layout.label_width,
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_DISPLAY_COMBO_PALETTE,
                items=list(view_model.palettes),
                default_value=view_model.settings.palette,
                width=self._layout.combo_width,
                callback=self._on_palette_changed,
            )

    @table_wrapper(columns=2)
    def _create_action_buttons(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_DISPLAY_BUTTON_CANCEL,
            label=self._language_manager["global.dialog.label.cancel"],
            callback=self._request_cancel,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_DISPLAY_BUTTON_OK,
            label=self._language_manager["global.dialog.label.ok"],
            callback=self._request_commit,
            width=-1,
        )

    def _install_navigation(self) -> None:
        """Wires Tab/Enter/Escape navigation over the controls and buttons."""
        self._navigator = DialogKeyboardNavigator(
            window_tag=self.tag,
            stops=[
                FocusStop.field(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION),
                FocusStop.field(TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS),
                FocusStop.field(TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN),
                FocusStop.field(TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC),
                FocusStop.field(TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE),
                FocusStop.field(TAG_SETTINGS_DISPLAY_COMBO_PALETTE),
                FocusStop.button(TAG_SETTINGS_DISPLAY_BUTTON_CANCEL, self._request_cancel),
                FocusStop.button(TAG_SETTINGS_DISPLAY_BUTTON_OK, self._request_commit),
            ],
            on_escape=self._request_cancel,
            key_router=self._router,
            shortcut_source=self._shortcuts,
        )
        self._navigator.install()

    def _teardown(self) -> None:
        if self._navigator is not None:
            self._navigator.dispose()
            self._navigator = None

    def _render(self) -> None:
        """Shows the standing selection, offering the size and frame controls while they apply."""
        view_model = self._require_view_model()
        dpg_configure_item(
            TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION,
            items=list(view_model.resolution_items),
            enabled=view_model.window_controls_enabled,
        )
        dpg_set_value(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION, view_model.current_resolution_item)
        dpg_configure_item(
            TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS,
            enabled=view_model.window_controls_enabled,
        )
        dpg_set_value(TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS, view_model.settings.window.borderless)
        dpg_set_value(TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN, view_model.settings.window.fullscreen)
        dpg_set_value(TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC, view_model.settings.vsync)
        dpg_configure_item(
            TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE,
            items=list(view_model.frame_rate_items(self._lbl_unlimited)),
        )
        dpg_set_value(
            TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE,
            view_model.current_frame_rate_item(self._lbl_unlimited),
        )
        dpg_configure_item(TAG_SETTINGS_DISPLAY_COMBO_PALETTE, items=list(view_model.palettes))
        dpg_set_value(TAG_SETTINGS_DISPLAY_COMBO_PALETTE, view_model.settings.palette)

    def _on_resolution_changed(self, _sender: Sender, app_data: str) -> None:
        view_model = self._require_view_model()
        resolution = view_model.resolution_for_item(app_data)
        self._emit_window(view_model.settings.window.with_resolution(resolution))

    def _on_borderless_changed(self, _sender: Sender, app_data: bool) -> None:
        window = self._require_view_model().settings.window
        self._emit_window(window.with_borderless(bool(app_data)))

    def _on_fullscreen_changed(self, _sender: Sender, app_data: bool) -> None:
        window = self._require_view_model().settings.window
        self._emit_window(window.with_fullscreen(bool(app_data)))

    def _on_vsync_changed(self, _sender: Sender, app_data: bool) -> None:
        settings = self._require_view_model().settings
        self._emit(settings.with_vsync(bool(app_data)))

    def _on_frame_rate_changed(self, _sender: Sender, app_data: str) -> None:
        view_model = self._require_view_model()
        frame_rate = view_model.frame_rate_for_item(app_data, self._lbl_unlimited)
        self._emit(view_model.settings.with_frame_rate(frame_rate))

    def _on_palette_changed(self, _sender: Sender, app_data: str) -> None:
        settings = self._require_view_model().settings
        self._emit(settings.with_palette(app_data))

    def _emit(self, settings: DisplaySettings) -> None:
        self.call(self.on_settings_changed, settings)

    def _emit_window(self, window: WindowMode) -> None:
        self._emit(self._require_view_model().settings.with_window(window))

    def _request_commit(self) -> None:
        self.call(self.on_commit)

    def _request_cancel(self) -> None:
        self.call(self.on_cancel)

    def _require_view_model(self) -> DisplaySettingsViewModel:
        """The settings on screen.

        Raises:
            SystemError: when the window is drawn before :meth:`open` seeds it.
        """
        if self._view_model is None:
            raise SystemError("The display settings window is drawn from a view model it was opened with")

        return self._view_model
