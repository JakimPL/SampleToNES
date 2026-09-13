from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.general.colors.text import TextColors
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.settings import (
    TAG_SETTINGS_NSF_BUTTON_BROWSE,
    TAG_SETTINGS_NSF_BUTTON_CANCEL,
    TAG_SETTINGS_NSF_BUTTON_EXPORT,
    TAG_SETTINGS_NSF_CHECKBOX_CHANNEL,
    TAG_SETTINGS_NSF_COMBO_REPEAT,
    TAG_SETTINGS_NSF_COMBO_SCHEME,
    TAG_SETTINGS_NSF_GROUP_DESTINATION,
    TAG_SETTINGS_NSF_GROUP_LOOP_FRAME,
    TAG_SETTINGS_NSF_INPUT_ARTIST,
    TAG_SETTINGS_NSF_INPUT_COPYRIGHT,
    TAG_SETTINGS_NSF_INPUT_LOOP_FRAME,
    TAG_SETTINGS_NSF_INPUT_TITLE,
    TAG_SETTINGS_NSF_PATH_DESTINATION,
    TAG_SETTINGS_NSF_TEXT_ARTIST_SIZE,
    TAG_SETTINGS_NSF_TEXT_COPYRIGHT_SIZE,
    TAG_SETTINGS_NSF_TEXT_FRAME_COUNT,
    TAG_SETTINGS_NSF_TEXT_LENGTH,
    TAG_SETTINGS_NSF_TEXT_NO_CHANNEL,
    TAG_SETTINGS_NSF_TEXT_SCHEME_DESCRIPTION,
    TAG_SETTINGS_NSF_TEXT_TITLE_SIZE,
    TAG_SETTINGS_NSF_WINDOW,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.ui.elements.field import labeled_field, subheader
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.path import GUIDestinationPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_delete_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.keyboard.focus.tree import is_item_active
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.nsf.information import NSFInformation
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

HEXADECIMAL_BASE: Final[int] = 16

ChoicesCallback = Callable[[NSFExportChoices], None]


@dataclass(frozen=True)
class HeaderField:
    """One of the header's text fields, as the dialog lays it out and edits it.

    Attributes:
        input_tag: The field the text is typed into.
        size_tag: The line stating the bytes the text takes.
        label: What the field is known by.
        read: The field's text, out of the header information.
        edit: The choices holding a typed text in the field.
    """

    input_tag: str
    size_tag: str
    label: str
    read: Callable[[NSFInformation], str]
    edit: Callable[[NSFExportChoices, str], NSFExportChoices]


class GUINSFExportWindow(GUIDialogWindow):
    """Modal form over writing a project or a reconstruction as an NSF program.

    The dialog sets the export up and hands it over: the program's text, the channels it sounds,
    how it repeats and how hard it is compressed are chosen here along with the file, and the
    export's own window reports the run that follows.

    Every control reports the whole edited choices through ``on_choices_changed``, which the owner
    reconciles and hands back, so the dialog shows the choices as they end up. A field being typed
    into keeps the text the reader types, and takes the text the header holds once it is left.
    """

    _fits_content = True

    def __init__(
        self,
        *,
        layout: SettingsLayout,
        path_colors: PathColors,
        text_colors: TextColors,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self._layout = layout
        self._path_colors = path_colors
        self._text_colors = text_colors
        self._status_bar = status_bar
        self._view_model: Optional[NSFExportViewModel] = None
        self._destination_text: Optional[GUIDestinationPathText] = None
        self._handler_tag = compose_tag(TAG_SETTINGS_NSF_WINDOW, SUF_HANDLER_REGISTRY)

        self.on_choices_changed: Optional[ChoicesCallback] = None
        self.on_browse: Optional[VoidCallback] = None
        self.on_export: Optional[VoidCallback] = None
        self.on_close: Optional[VoidCallback] = None

        self._repeats_by_label: Dict[str, NSFRepeat] = {}
        self._schemes_by_label: Dict[str, CompressionScheme] = {}

        self._fmt_text_size = language_manager["settings.nsf.template.text_size"]
        self._fmt_frame = language_manager["settings.nsf.template.frame"]
        self._fmt_frame_count = language_manager["settings.nsf.template.frame_count"]
        self._fmt_length = language_manager["settings.nsf.template.length"]
        self._msg_destination = language_manager["global.status.message.destination"]
        self._fields: Tuple[HeaderField, ...] = (
            HeaderField(
                input_tag=TAG_SETTINGS_NSF_INPUT_TITLE,
                size_tag=TAG_SETTINGS_NSF_TEXT_TITLE_SIZE,
                label=language_manager["settings.nsf.label.title"],
                read=lambda information: information.title,
                edit=NSFExportChoices.with_title,
            ),
            HeaderField(
                input_tag=TAG_SETTINGS_NSF_INPUT_ARTIST,
                size_tag=TAG_SETTINGS_NSF_TEXT_ARTIST_SIZE,
                label=language_manager["settings.nsf.label.artist"],
                read=lambda information: information.artist,
                edit=NSFExportChoices.with_artist,
            ),
            HeaderField(
                input_tag=TAG_SETTINGS_NSF_INPUT_COPYRIGHT,
                size_tag=TAG_SETTINGS_NSF_TEXT_COPYRIGHT_SIZE,
                label=language_manager["settings.nsf.label.copyright"],
                read=lambda information: information.copyright,
                edit=NSFExportChoices.with_copyright,
            ),
        )
        self._repeat_labels: Dict[NSFRepeat, str] = {
            NSFRepeat.ONCE: language_manager["settings.nsf.label.repeat_once"],
            NSFRepeat.FROM_START: language_manager["settings.nsf.label.repeat_from_start"],
            NSFRepeat.FROM_FRAME: language_manager["settings.nsf.label.repeat_from_frame"],
        }
        self._scheme_labels: Dict[CompressionScheme, str] = {
            CompressionScheme.NONE: language_manager["settings.nsf.label.scheme_none"],
            CompressionScheme.RUNS: language_manager["settings.nsf.label.scheme_runs"],
            CompressionScheme.INSTRUMENTS: language_manager["settings.nsf.label.scheme_instruments"],
            CompressionScheme.SEARCH: language_manager["settings.nsf.label.scheme_search"],
        }
        self._scheme_descriptions: Dict[CompressionScheme, str] = {
            CompressionScheme.NONE: language_manager["settings.nsf.message.scheme_none"],
            CompressionScheme.RUNS: language_manager["settings.nsf.message.scheme_runs"],
            CompressionScheme.INSTRUMENTS: language_manager["settings.nsf.message.scheme_instruments"],
            CompressionScheme.SEARCH: language_manager["settings.nsf.message.scheme_search"],
        }

        super().__init__(
            tag=TAG_SETTINGS_NSF_WINDOW,
            width=layout.nsf.window.width,
            height=layout.nsf.window.height,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def open(self, view_model: NSFExportViewModel) -> None:
        """Shows the window seeded with the export being set up."""
        self._view_model = view_model
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The drawn values are seeded by :meth:`open` before the tree rebuilds."""

    def update_view(self, view_model: NSFExportViewModel) -> None:
        """Re-draws the open window from the choices the export stands at."""
        self._view_model = view_model
        self._render()

    def create_window(self) -> None:
        with self.dialog_window(
            label=self._language_manager["settings.nsf.title.window_title"],
            on_close=self._request_close,
        ):
            self._create_program_section()
            dpg.add_separator()
            self._create_channels_section()
            dpg.add_separator()
            self._create_playback_section()
            dpg.add_separator()
            self._create_compression_section()
            dpg.add_separator()
            self._create_destination()
            dpg.add_separator()
            self._create_buttons()

        self._create_field_handlers()
        self._bind_dialog_theme(
            TAG_SETTINGS_NSF_INPUT_TITLE,
            TAG_SETTINGS_NSF_INPUT_ARTIST,
            TAG_SETTINGS_NSF_INPUT_COPYRIGHT,
            TAG_SETTINGS_NSF_COMBO_REPEAT,
            TAG_SETTINGS_NSF_INPUT_LOOP_FRAME,
            TAG_SETTINGS_NSF_COMBO_SCHEME,
        )

        self._render()
        self._install_navigation(
            [
                *(FocusStop.field(field.input_tag) for field in self._fields),
                *(FocusStop.field(self._channel_tag(channel)) for channel in ChannelName.items()),
                FocusStop.field(TAG_SETTINGS_NSF_COMBO_REPEAT),
                FocusStop.field(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME),
                FocusStop.field(TAG_SETTINGS_NSF_COMBO_SCHEME),
                FocusStop.button(TAG_SETTINGS_NSF_BUTTON_BROWSE, self._request_destination),
                FocusStop.button(TAG_SETTINGS_NSF_BUTTON_CANCEL, self._request_close),
                FocusStop.button(TAG_SETTINGS_NSF_BUTTON_EXPORT, self._request_export),
            ],
            on_escape=self._request_close,
        )

    def _create_program_section(self) -> None:
        subheader(self._language_manager["settings.nsf.title.section_program"])
        for field in self._fields:
            with labeled_field(field.label, self._layout.label_width):
                dpg.add_input_text(
                    tag=field.input_tag,
                    width=self._layout.nsf.text_width,
                    callback=self._on_text_changed,
                    user_data=field,
                )
                dpg.add_text("", tag=field.size_tag)

            FontRegistry.bind_to_item(field.size_tag, Font.MONO_SMALL)
            dpg_set_palette_color(field.size_tag, self._text_colors.disabled)

    def _create_channels_section(self) -> None:
        subheader(self._language_manager["settings.nsf.title.section_channels"])
        self._create_channel_checkboxes()
        dpg.add_text(
            self._language_manager["settings.nsf.message.no_channel"],
            tag=TAG_SETTINGS_NSF_TEXT_NO_CHANNEL,
        )
        dpg_set_palette_color(TAG_SETTINGS_NSF_TEXT_NO_CHANNEL, self._text_colors.highlight)

    @table_wrapper(columns=len(ChannelName.items()), height=0)
    def _create_channel_checkboxes(self) -> None:
        """Lays the channels out in one row, each tinted in its own color where the source sounds it."""
        view_model = self._require_view_model()
        for channel in ChannelName.items():
            tag = self._channel_tag(channel)
            dpg.add_checkbox(
                tag=tag,
                label=channel_label(self._language_manager, channel),
                callback=self._on_channel_changed,
                user_data=channel,
            )
            if view_model.channel_offered(channel):
                ThemeRegistry.get(CHANNEL_THEME_TAGS[channel]).bind_to_item(tag)

    def _create_playback_section(self) -> None:
        subheader(self._language_manager["settings.nsf.title.section_playback"])
        with labeled_field(
            self._language_manager["settings.nsf.label.repeat"],
            self._layout.label_width,
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_NSF_COMBO_REPEAT,
                items=[],
                width=self._layout.combo_width,
                callback=self._on_repeat_changed,
            )

        with (
            dpg.group(tag=TAG_SETTINGS_NSF_GROUP_LOOP_FRAME),
            labeled_field(
                self._language_manager["settings.nsf.label.loop_frame"],
                self._layout.label_width,
            ),
        ):
            dpg.add_input_text(
                tag=TAG_SETTINGS_NSF_INPUT_LOOP_FRAME,
                width=self._layout.nsf.frame_width,
                hexadecimal=True,
                uppercase=True,
                no_spaces=True,
                callback=self._on_loop_frame_changed,
            )
            dpg.add_text("", tag=TAG_SETTINGS_NSF_TEXT_FRAME_COUNT)

        FontRegistry.bind_to_item(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME, Font.MONO)
        FontRegistry.bind_to_item(TAG_SETTINGS_NSF_TEXT_FRAME_COUNT, Font.MONO)
        with labeled_field(
            self._language_manager["settings.nsf.label.length"],
            self._layout.label_width,
        ):
            dpg.add_text("", tag=TAG_SETTINGS_NSF_TEXT_LENGTH)
            FontRegistry.bind_to_item(TAG_SETTINGS_NSF_TEXT_LENGTH, Font.MONO)

    def _create_compression_section(self) -> None:
        subheader(self._language_manager["settings.nsf.title.section_compression"])
        with labeled_field(
            self._language_manager["settings.nsf.label.scheme"],
            self._layout.label_width,
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_NSF_COMBO_SCHEME,
                items=[],
                width=self._layout.combo_width,
                callback=self._on_scheme_changed,
            )

        dpg.add_text(
            "",
            tag=TAG_SETTINGS_NSF_TEXT_SCHEME_DESCRIPTION,
            indent=self._layout.label_width,
            wrap=0,
        )
        FontRegistry.bind_to_item(TAG_SETTINGS_NSF_TEXT_SCHEME_DESCRIPTION, Font.REGULAR_SMALL)
        dpg_set_palette_color(TAG_SETTINGS_NSF_TEXT_SCHEME_DESCRIPTION, self._text_colors.disabled)

    def _create_destination(self) -> None:
        """Lays out the file the export writes, with the browse button leading the path it stands at."""
        with labeled_field(
            self._language_manager["settings.nsf.label.destination"],
            self._layout.label_width,
        ):
            dpg.add_group(horizontal=True, tag=TAG_SETTINGS_NSF_GROUP_DESTINATION)

        GUIButton(
            tag=TAG_SETTINGS_NSF_BUTTON_BROWSE,
            label=self._language_manager["settings.nsf.label.browse_button"],
            parent=TAG_SETTINGS_NSF_GROUP_DESTINATION,
            callback=self._request_destination,
        )
        self._destination_text = GUIDestinationPathText(
            tag=TAG_SETTINGS_NSF_PATH_DESTINATION,
            path=self._require_view_model().destination,
            parent=TAG_SETTINGS_NSF_GROUP_DESTINATION,
            color=self._path_colors.default,
            hover_color=self._path_colors.hover,
            status_message=self._msg_destination,
            font=Font.REGULAR_SMALL,
            status_bar=self._status_bar,
        )

    @table_wrapper(columns=2)
    def _create_buttons(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_NSF_BUTTON_CANCEL,
            label=self._language_manager["global.dialog.label.cancel"],
            callback=self._request_close,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_NSF_BUTTON_EXPORT,
            label=self._language_manager["settings.nsf.label.export_button"],
            callback=self._request_export,
            width=-1,
        )

    def _create_field_handlers(self) -> None:
        """Draws a typed field again once it is left, so it shows the text the header holds."""
        with dpg.item_handler_registry(tag=self._handler_tag):
            dpg.add_item_deactivated_after_edit_handler(callback=self._render)

        for tag in (*(field.input_tag for field in self._fields), TAG_SETTINGS_NSF_INPUT_LOOP_FRAME):
            dpg.bind_item_handler_registry(tag, self._handler_tag)

    def _render(self) -> None:
        """Draws the choices as they reconciled, around whatever field is being typed into."""
        view_model = self._require_view_model()
        self._render_fields(view_model)
        self._render_channels(view_model)
        self._render_repeat(view_model)
        self._render_scheme(view_model)
        if self._destination_text is not None:
            self._destination_text.set_path(view_model.destination)

        dpg_configure_item(TAG_SETTINGS_NSF_BUTTON_EXPORT, enabled=view_model.export_enabled)

    def _render_fields(self, view_model: NSFExportViewModel) -> None:
        for field in self._fields:
            text = field.read(view_model.choices.information)
            self._settle_input(field.input_tag, text)
            dpg_set_value(field.size_tag, view_model.text_size_label(text, self._fmt_text_size))

    def _render_channels(self, view_model: NSFExportViewModel) -> None:
        for channel in ChannelName.items():
            tag = self._channel_tag(channel)
            dpg_configure_item(tag, enabled=view_model.channel_offered(channel))
            dpg_set_value(tag, view_model.channel_sounded(channel))

        dpg_configure_item(TAG_SETTINGS_NSF_TEXT_NO_CHANNEL, show=not view_model.export_enabled)

    def _render_repeat(self, view_model: NSFExportViewModel) -> None:
        self._repeats_by_label = {self._repeat_labels[repeat]: repeat for repeat in view_model.repeats}
        dpg_configure_item(TAG_SETTINGS_NSF_COMBO_REPEAT, items=list(self._repeats_by_label))
        dpg_set_value(TAG_SETTINGS_NSF_COMBO_REPEAT, self._repeat_labels[view_model.choices.repeat])
        dpg_configure_item(TAG_SETTINGS_NSF_GROUP_LOOP_FRAME, show=view_model.loop_frame_visible)
        dpg_configure_item(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME, enabled=view_model.loop_frame_visible)
        self._settle_input(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME, view_model.loop_frame_label(self._fmt_frame))
        dpg_set_value(TAG_SETTINGS_NSF_TEXT_FRAME_COUNT, view_model.frame_count_label(self._fmt_frame_count))
        dpg_set_value(TAG_SETTINGS_NSF_TEXT_LENGTH, view_model.length_label(self._fmt_length))

    def _render_scheme(self, view_model: NSFExportViewModel) -> None:
        scheme = view_model.choices.scheme
        self._schemes_by_label = {self._scheme_labels[offered]: offered for offered in view_model.schemes}
        dpg_configure_item(TAG_SETTINGS_NSF_COMBO_SCHEME, items=list(self._schemes_by_label))
        dpg_set_value(TAG_SETTINGS_NSF_COMBO_SCHEME, self._scheme_labels[scheme])
        dpg_set_value(TAG_SETTINGS_NSF_TEXT_SCHEME_DESCRIPTION, self._scheme_descriptions[scheme])

    @staticmethod
    def _settle_input(tag: str, text: str) -> None:
        """Puts ``text`` in a field the reader has left.

        DearPyGui reports a field's typed text again on every frame once its value is set while it
        is being typed into, so the field being edited keeps its own text until it is left.
        """
        if dpg.does_item_exist(tag) and not is_item_active(tag):
            dpg_set_value(tag, text)

    def _on_text_changed(self, _sender: Sender, app_data: str, field: HeaderField) -> None:
        self._emit(field.edit(self._choices(), app_data))

    def _on_channel_changed(self, _sender: Sender, app_data: bool, channel: ChannelName) -> None:
        view_model = self._require_view_model()
        self._emit(view_model.choices.with_channel(channel, bool(app_data), view_model.offer))

    def _on_repeat_changed(self, _sender: Sender, app_data: str) -> None:
        view_model = self._require_view_model()
        self._emit(view_model.choices.with_repeat(self._repeats_by_label[app_data], view_model.offer))

    def _on_loop_frame_changed(self, _sender: Sender, app_data: str) -> None:
        """Takes the frame typed in hexadecimal, once the field holds a number to read."""
        try:
            frame = int(app_data, HEXADECIMAL_BASE)
        except ValueError:
            return

        view_model = self._require_view_model()
        self._emit(view_model.choices.with_loop_frame(frame, view_model.offer))

    def _on_scheme_changed(self, _sender: Sender, app_data: str) -> None:
        view_model = self._require_view_model()
        self._emit(view_model.choices.with_scheme(self._schemes_by_label[app_data], view_model.offer))

    def _emit(self, choices: NSFExportChoices) -> None:
        self.call(self.on_choices_changed, choices)

    def _request_destination(self) -> None:
        self.call(self.on_browse)

    def _request_export(self) -> None:
        if self._require_view_model().export_enabled:
            self.call(self.on_export)

    def _request_close(self) -> None:
        self.call(self.on_close)

    def _teardown(self) -> None:
        """Releases the keyboard claim and the field handlers of the appearance being torn down."""
        super()._teardown()
        dpg_delete_item(self._handler_tag)

    def _choices(self) -> NSFExportChoices:
        return self._require_view_model().choices

    @staticmethod
    def _channel_tag(channel: ChannelName) -> str:
        return compose_tag(TAG_SETTINGS_NSF_CHECKBOX_CHANNEL, channel.value)

    def _require_view_model(self) -> NSFExportViewModel:
        """The export on screen.

        Raises:
            SystemError: when the window is drawn before :meth:`open` seeds it.
        """
        if self._view_model is None:
            raise SystemError("The NSF export window is drawn from a view model it was opened with")

        return self._view_model
