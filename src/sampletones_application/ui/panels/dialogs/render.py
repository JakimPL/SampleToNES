from typing import Any, Callable, Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.tags.settings import (
    TAG_SETTINGS_RENDER_BUTTON_BROWSE,
    TAG_SETTINGS_RENDER_BUTTON_CANCEL,
    TAG_SETTINGS_RENDER_BUTTON_CLOSE,
    TAG_SETTINGS_RENDER_BUTTON_START,
    TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE,
    TAG_SETTINGS_RENDER_COMBO_BITRATE,
    TAG_SETTINGS_RENDER_COMBO_DEPTH,
    TAG_SETTINGS_RENDER_COMBO_FORMAT,
    TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE,
    TAG_SETTINGS_RENDER_GROUP_BITRATE,
    TAG_SETTINGS_RENDER_GROUP_DEPTH,
    TAG_SETTINGS_RENDER_GROUP_DESTINATION,
    TAG_SETTINGS_RENDER_GROUP_PROGRESS,
    TAG_SETTINGS_RENDER_GROUP_SETUP,
    TAG_SETTINGS_RENDER_PATH_DESTINATION,
    TAG_SETTINGS_RENDER_PROGRESS,
    TAG_SETTINGS_RENDER_TEXT_DURATION,
    TAG_SETTINGS_RENDER_TEXT_STATUS,
    TAG_SETTINGS_RENDER_WINDOW,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.shared.render import (
    SongRenderSettings,
    SongRenderViewModel,
)
from sampletones_core.audio.writers import AudioDepth, AudioFormat
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

SettingsCallback = Callable[[SongRenderSettings], None]


class GUIRenderWindow(GUIDialogWindow):
    """Modal form over writing the open song to an audio file.

    The dialog has two faces and shows one at a time: the setup, where the file is described and
    the render is started, and the progress, where the running pass reports itself and takes a
    stop. Which one stands is the phase the view model carries, so the window draws whatever it
    is handed.

    Every control reports the whole edited state through ``on_settings_changed``, which the owner
    reconciles and hands back — so what a container accepts decides what the next combo offers,
    and the dialog shows the choices as they end up rather than as they were asked for.
    """

    def __init__(
        self,
        *,
        layout: SettingsLayout,
        path_colors: PathColors,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self._layout = layout
        self._path_colors = path_colors
        self._status_bar = status_bar
        self._view_model: Optional[SongRenderViewModel] = None
        self._destination_text: Optional[GUIPathText] = None

        self.on_settings_changed: Optional[SettingsCallback] = None
        self.on_browse: Optional[VoidCallback] = None
        self.on_render: Optional[VoidCallback] = None
        self.on_cancel: Optional[VoidCallback] = None
        self.on_close: Optional[VoidCallback] = None

        self._formats_by_label: Dict[str, AudioFormat] = {}
        self._sample_rates_by_label: Dict[str, int] = {}
        self._depths_by_label: Dict[str, AudioDepth] = {}
        self._bitrates_by_label: Dict[str, int] = {}

        self._fmt_sample_rate = language_manager["settings.render.template.sample_rate"]
        self._fmt_bitrate = language_manager["settings.render.template.bitrate"]
        self._msg_path = language_manager["global.status.message.path"]
        self._format_labels: Dict[AudioFormat, str] = {
            AudioFormat.WAVE: language_manager["settings.render.label.format_wave"],
            AudioFormat.MP3: language_manager["settings.render.label.format_mp3"],
        }
        self._depth_labels: Dict[AudioDepth, str] = {
            AudioDepth.PCM_U8: language_manager["settings.render.label.depth_pcm_u8"],
            AudioDepth.PCM_16: language_manager["settings.render.label.depth_pcm_16"],
            AudioDepth.PCM_24: language_manager["settings.render.label.depth_pcm_24"],
            AudioDepth.PCM_32: language_manager["settings.render.label.depth_pcm_32"],
            AudioDepth.FLOAT_32: language_manager["settings.render.label.depth_float_32"],
        }

        super().__init__(
            tag=TAG_SETTINGS_RENDER_WINDOW,
            width=layout.render.window.width,
            height=layout.render.window.height,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def open(self, view_model: SongRenderViewModel) -> None:
        """Shows the window seeded with the render being set up."""
        self._view_model = view_model
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The rendered values are seeded by :meth:`open` before the tree rebuilds."""

    def update_view(self, view_model: SongRenderViewModel) -> None:
        """Re-seeds the controls of the open window from where the render stands."""
        self._view_model = view_model
        self._render()

    def create_window(self) -> None:
        with self.dialog_window(
            label=self._language_manager["settings.render.title.window_title"],
            on_close=self._request_close,
        ):
            self._create_setup()
            self._create_progress()

        self._bind_dialog_theme(
            TAG_SETTINGS_RENDER_COMBO_FORMAT,
            TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE,
            TAG_SETTINGS_RENDER_COMBO_DEPTH,
            TAG_SETTINGS_RENDER_COMBO_BITRATE,
        )

        self._render()
        self._install_navigation(
            [
                FocusStop.field(TAG_SETTINGS_RENDER_COMBO_FORMAT),
                FocusStop.field(TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE),
                FocusStop.field(TAG_SETTINGS_RENDER_COMBO_DEPTH),
                FocusStop.field(TAG_SETTINGS_RENDER_COMBO_BITRATE),
                FocusStop.field(TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE),
                FocusStop.button(TAG_SETTINGS_RENDER_BUTTON_BROWSE, self._request_destination),
                FocusStop.button(TAG_SETTINGS_RENDER_BUTTON_CLOSE, self._request_close),
                FocusStop.button(TAG_SETTINGS_RENDER_BUTTON_START, self._request_render),
                FocusStop.button(TAG_SETTINGS_RENDER_BUTTON_CANCEL, self._request_cancel),
            ],
            on_escape=self._request_close,
        )

    def _create_setup(self) -> None:
        with dpg.group(tag=TAG_SETTINGS_RENDER_GROUP_SETUP):
            self._create_format_selection()
            self._create_sample_rate_selection()
            self._create_depth_selection()
            self._create_bitrate_selection()
            self._create_normalize_switch()
            self._create_duration()
            dpg.add_separator()
            self._create_destination()
            dpg.add_separator()
            self._create_setup_buttons()

    def _create_format_selection(self) -> None:
        with labeled_field(
            self._language_manager["settings.render.label.format"],
            self._layout.label_width,
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_RENDER_COMBO_FORMAT,
                items=[],
                width=self._layout.combo_width,
                callback=self._on_format_changed,
            )

    def _create_sample_rate_selection(self) -> None:
        with labeled_field(
            self._language_manager["settings.render.label.sample_rate"],
            self._layout.label_width,
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE,
                items=[],
                width=self._layout.combo_width,
                callback=self._on_sample_rate_changed,
            )

    def _create_depth_selection(self) -> None:
        with (
            dpg.group(tag=TAG_SETTINGS_RENDER_GROUP_DEPTH),
            labeled_field(
                self._language_manager["settings.render.label.depth"],
                self._layout.label_width,
            ),
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_RENDER_COMBO_DEPTH,
                items=[],
                width=self._layout.combo_width,
                callback=self._on_depth_changed,
            )

    def _create_bitrate_selection(self) -> None:
        with (
            dpg.group(tag=TAG_SETTINGS_RENDER_GROUP_BITRATE),
            labeled_field(
                self._language_manager["settings.render.label.bitrate"],
                self._layout.label_width,
            ),
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_RENDER_COMBO_BITRATE,
                items=[],
                width=self._layout.combo_width,
                callback=self._on_bitrate_changed,
            )

    def _create_normalize_switch(self) -> None:
        dpg.add_checkbox(
            tag=TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE,
            label=self._language_manager["settings.render.label.normalize"],
            callback=self._on_normalize_changed,
        )

    def _create_duration(self) -> None:
        with labeled_field(
            self._language_manager["settings.render.label.duration"],
            self._layout.label_width,
        ):
            dpg.add_text("", tag=TAG_SETTINGS_RENDER_TEXT_DURATION)
            FontRegistry.bind_to_item(TAG_SETTINGS_RENDER_TEXT_DURATION, Font.MONO)

    def _create_destination(self) -> None:
        """Lays out the file a render writes, with the browse button beside the path it stands at.

        The button leads the row so it holds its place whatever the path reads, and the path
        follows it as the answer to what the button asks.
        """
        with labeled_field(
            self._language_manager["settings.render.label.destination"],
            self._layout.label_width,
        ):
            dpg.add_group(horizontal=True, tag=TAG_SETTINGS_RENDER_GROUP_DESTINATION)

        GUIButton(
            tag=TAG_SETTINGS_RENDER_BUTTON_BROWSE,
            label=self._language_manager["settings.render.label.browse_button"],
            parent=TAG_SETTINGS_RENDER_GROUP_DESTINATION,
            callback=self._request_destination,
        )
        self._destination_text = GUIPathText(
            tag=TAG_SETTINGS_RENDER_PATH_DESTINATION,
            path=self._require_view_model().destination,
            parent=TAG_SETTINGS_RENDER_GROUP_DESTINATION,
            color=self._path_colors.default,
            hover_color=self._path_colors.hover,
            status_message=self._msg_path,
            font=Font.REGULAR_SMALL,
            status_bar=self._status_bar,
        )

    @table_wrapper(columns=2)
    def _create_setup_buttons(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_RENDER_BUTTON_CLOSE,
            label=self._language_manager["global.dialog.label.cancel"],
            callback=self._request_close,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_RENDER_BUTTON_START,
            label=self._language_manager["settings.render.label.render_button"],
            callback=self._request_render,
            width=-1,
        )

    def _create_progress(self) -> None:
        with dpg.group(tag=TAG_SETTINGS_RENDER_GROUP_PROGRESS, show=False):
            dpg.add_text("", tag=TAG_SETTINGS_RENDER_TEXT_STATUS)
            FontRegistry.bind_to_item(TAG_SETTINGS_RENDER_TEXT_STATUS, Font.MONO_SMALL)
            dpg.add_progress_bar(
                tag=TAG_SETTINGS_RENDER_PROGRESS,
                default_value=0.0,
                width=-1,
            )
            FontRegistry.bind_to_item(TAG_SETTINGS_RENDER_PROGRESS, Font.MONO)
            dpg.add_separator()
            GUIButton(
                tag=TAG_SETTINGS_RENDER_BUTTON_CANCEL,
                label=self._language_manager["global.dialog.label.cancel"],
                callback=self._request_cancel,
                width=-1,
            )

    def _render(self) -> None:
        """Shows the face the phase calls for, with each choice standing at what it reconciled to."""
        view_model = self._require_view_model()
        self._render_setup(view_model)
        self._render_progress(view_model)

    def _render_setup(self, view_model: SongRenderViewModel) -> None:
        dpg_configure_item(TAG_SETTINGS_RENDER_GROUP_SETUP, show=view_model.setup_visible)
        self._render_formats(view_model)
        self._render_sample_rates(view_model)
        self._render_depths(view_model)
        self._render_bitrates(view_model)
        dpg_configure_item(
            TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE,
            enabled=view_model.setup_visible,
        )
        dpg_set_value(TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE, view_model.settings.normalize)
        dpg_set_value(TAG_SETTINGS_RENDER_TEXT_DURATION, view_model.duration_label)
        if self._destination_text is not None:
            self._destination_text.set_path(view_model.destination)

        dpg_configure_item(TAG_SETTINGS_RENDER_BUTTON_BROWSE, enabled=view_model.setup_visible)
        dpg_configure_item(TAG_SETTINGS_RENDER_BUTTON_CLOSE, enabled=view_model.setup_visible)
        dpg_configure_item(TAG_SETTINGS_RENDER_BUTTON_START, enabled=view_model.render_enabled)

    def _render_formats(self, view_model: SongRenderViewModel) -> None:
        self._formats_by_label = {
            self._format_labels[audio_format]: audio_format for audio_format in view_model.formats
        }
        dpg_configure_item(
            TAG_SETTINGS_RENDER_COMBO_FORMAT,
            items=list(self._formats_by_label),
            enabled=view_model.setup_visible,
        )
        dpg_set_value(
            TAG_SETTINGS_RENDER_COMBO_FORMAT,
            self._format_labels[view_model.spec.audio_format],
        )

    def _render_sample_rates(self, view_model: SongRenderViewModel) -> None:
        self._sample_rates_by_label = dict(
            zip(
                view_model.sample_rate_labels(self._fmt_sample_rate),
                view_model.sample_rates,
            )
        )
        dpg_configure_item(
            TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE,
            items=list(self._sample_rates_by_label),
            enabled=view_model.setup_visible,
        )
        dpg_set_value(
            TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE,
            view_model.sample_rate_label(self._fmt_sample_rate),
        )

    def _render_depths(self, view_model: SongRenderViewModel) -> None:
        self._depths_by_label = {self._depth_labels[depth]: depth for depth in view_model.depths}
        depth = view_model.settings.depth
        dpg_configure_item(TAG_SETTINGS_RENDER_GROUP_DEPTH, show=view_model.depth_visible)
        dpg_configure_item(
            TAG_SETTINGS_RENDER_COMBO_DEPTH,
            items=list(self._depths_by_label),
            enabled=view_model.depth_enabled,
        )
        dpg_set_value(
            TAG_SETTINGS_RENDER_COMBO_DEPTH,
            self._depth_labels[depth] if depth is not None else "",
        )

    def _render_bitrates(self, view_model: SongRenderViewModel) -> None:
        self._bitrates_by_label = dict(
            zip(
                view_model.bitrate_labels(self._fmt_bitrate),
                view_model.bitrates,
            )
        )
        dpg_configure_item(TAG_SETTINGS_RENDER_GROUP_BITRATE, show=view_model.bitrate_visible)
        dpg_configure_item(
            TAG_SETTINGS_RENDER_COMBO_BITRATE,
            items=list(self._bitrates_by_label),
            enabled=view_model.bitrate_enabled,
        )
        dpg_set_value(
            TAG_SETTINGS_RENDER_COMBO_BITRATE,
            view_model.bitrate_label(self._fmt_bitrate),
        )

    def _render_progress(self, view_model: SongRenderViewModel) -> None:
        dpg_configure_item(TAG_SETTINGS_RENDER_GROUP_PROGRESS, show=view_model.progress_visible)
        dpg_set_value(TAG_SETTINGS_RENDER_TEXT_STATUS, view_model.status_text)
        dpg_set_value(TAG_SETTINGS_RENDER_PROGRESS, view_model.progress)
        dpg_configure_item(TAG_SETTINGS_RENDER_PROGRESS, overlay=view_model.progress_overlay)
        dpg_configure_item(TAG_SETTINGS_RENDER_BUTTON_CANCEL, enabled=view_model.cancel_enabled)

    def _on_format_changed(self, _sender: Sender, app_data: str) -> None:
        self._emit(self._settings().with_format(self._formats_by_label[app_data]))

    def _on_sample_rate_changed(self, _sender: Sender, app_data: str) -> None:
        self._emit(self._settings().with_sample_rate(self._sample_rates_by_label[app_data]))

    def _on_depth_changed(self, _sender: Sender, app_data: str) -> None:
        self._emit(self._settings().with_depth(self._depths_by_label[app_data]))

    def _on_bitrate_changed(self, _sender: Sender, app_data: str) -> None:
        self._emit(self._settings().with_bitrate(self._bitrates_by_label[app_data]))

    def _on_normalize_changed(self, _sender: Sender, app_data: bool) -> None:
        self._emit(self._settings().with_normalize(bool(app_data)))

    def _emit(self, settings: SongRenderSettings) -> None:
        self.call(self.on_settings_changed, settings)

    def _request_destination(self) -> None:
        self.call(self.on_browse)

    def _request_render(self) -> None:
        self.call(self.on_render)

    def _request_cancel(self) -> None:
        self.call(self.on_cancel)

    def _request_close(self) -> None:
        """Answers Escape and the title bar: a setup is done with, a running render is asked to stop.

        A render already stopping, and one that has reported its outcome, answer neither — what
        they are waiting for is the service, which arrives on its own.
        """
        view_model = self._require_view_model()
        if view_model.cancel_enabled:
            self._request_cancel()
        elif view_model.setup_visible:
            self.call(self.on_close)

    def _settings(self) -> SongRenderSettings:
        return self._require_view_model().settings

    def _require_view_model(self) -> SongRenderViewModel:
        """The render on screen.

        Raises:
            SystemError: when the window is drawn before :meth:`open` seeds it.
        """
        if self._view_model is None:
            raise SystemError("The render window is drawn from a view model it was opened with")

        return self._view_model
