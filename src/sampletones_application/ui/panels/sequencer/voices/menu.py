from typing import Callable, Final, List, Optional, Protocol, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import (
    channel_label,
    context_label,
    context_text,
)
from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.elements.sequencer import (
    SequencerVoicesElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.elements.context_menu import (
    add_detail_items,
    add_play_menu_item,
    context_menu,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.panels.sequencer.voices.moves import (
    VOICE_MOVES,
    VoiceMove,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.view_model.sequencer.voices import VoiceSelection
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.callback import StringCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

NO_INSTRUMENTS: Final[Tuple[Optional[ChannelName], ...]] = ()

NO_CHANNELS: Final[Tuple[ChannelName, ...]] = ()


class VoicesMenuHost(Protocol):
    """What the voices panel states to the menus raised over its list.

    The hooks are the panel's own, so the coordinator keeps wiring them where it already does, and
    a menu reads whichever answer stands at the moment it opens.
    """

    sample_footprint: Optional[Callable[[str], Optional[SampleFootprintViewModel]]]
    voice_instruments: Optional[Callable[[str], Tuple[Optional[ChannelName], ...]]]
    instrument_channels: Optional[Callable[[str], Tuple[ChannelName, ...]]]
    on_sample_edit_requested: Optional[StringCallback]
    on_duplicate_requested: Optional[StringCallback]
    on_remove_requested: Optional[StringCallback]
    on_play_requested: Optional[StringCallback]
    on_move_requested: Optional[Callable[[str, int], None]]
    on_new_instrument_requested: Optional[VoidCallback]
    on_add_sample_requested: Optional[VoidCallback]
    on_import_instrument_requested: Optional[VoidCallback]
    on_export_instrument_requested: Optional[Callable[[str, Optional[ChannelName]], None]]
    on_instrument_from_channel_requested: Optional[Callable[[str, ChannelName], None]]

    @property
    def voice_count(self) -> int: ...

    def start_rename(self, voice_id: str) -> None: ...


class VoicesMenu(CallbackMixin):
    """Every menu the voice list offers, wherever a reader raised it.

    Two sections make up the whole: the ways a voice comes into the pool, and what the voice a
    reader named can do. A door composes the sections it wants — the list's own menu prints the
    pool alone, a row prints both, the menu bar's **Edit** menu prints the voice's actions and the
    **Voice** group prints the pool above them — so an action is stated once and reaches all of
    them.

    What a menu offers about a voice is asked for as it opens: the byte figures, the instruments an
    export would write, the channels a new instrument could be written from. Reading them at that
    moment keeps what a menu prints and what a click does one answer.
    """

    def __init__(
        self,
        panel: VoicesMenuHost,
        *,
        language_manager: LanguageManager,
        shortcut_source: ShortcutSource,
        detail_color: BaseColor,
    ) -> None:
        self._panel = panel
        self._language_manager = language_manager
        self._shortcuts = shortcut_source
        self._detail_color = detail_color
        self._lbl_sample_size = context_label(language_manager, ContextElements.SAMPLE_SIZE)
        self._tpl_size_bytes = context_text(language_manager, TextType.TEMPLATE, ContextElements.SIZE_BYTES)
        self._tip_size_bytes = context_text(language_manager, TextType.TOOLTIP, ContextElements.SIZE_BYTES)

    def show_for(self, target: VoiceSelection) -> None:
        """Raises the menu of one voice: what it is, what it costs, and what can be done with it.

        A row is where a reader already is, so the ways a voice comes in stay within reach below
        the voice's own actions.
        """
        with context_menu():
            header = dpg.add_text(target.label)
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            add_detail_items(
                self._footprint_items(target.voice_id),
                color=self._detail_color,
                tooltip=self._tip_size_bytes,
            )
            dpg.add_separator()
            add_play_menu_item(
                context_label(self._language_manager, ContextElements.PLAY),
                lambda: self.call(
                    self._panel.on_play_requested,
                    target.voice_id,
                ),
            )
            dpg.add_separator()
            self.add_action_items(target)
            dpg.add_separator()
            self.add_pool_items()

    def show_pool(self) -> None:
        """Raises the list's own menu, which prints the ways a voice comes in."""
        with context_menu():
            self.add_pool_items()

    def add_pool_items(self) -> None:
        """Builds the ways a voice comes into the pool, in the order each menu prints them.

        A voice is written by hand, converted from a recording, or brought from a tracker, and
        the three stand apart from the actions a listed voice offers, since each answers with an
        entry the list did not hold. Every door onto the list prints this section, so a reader
        reaches it from the list and from a row alike.
        """
        dpg.add_menu_item(
            label=self._label(SequencerVoicesElements.NEW_INSTRUMENT),
            shortcut=self._shortcuts.display(ShortcutId.NEW_INSTRUMENT),
            callback=lambda: self.call(self._panel.on_new_instrument_requested),
        )
        dpg.add_menu_item(
            label=self._label(SequencerVoicesElements.ADD_SAMPLE),
            shortcut=self._shortcuts.display(ShortcutId.ADD_SAMPLE_FROM_FILE),
            callback=lambda: self.call(self._panel.on_add_sample_requested),
        )
        dpg.add_menu_item(
            label=self._label(SequencerVoicesElements.IMPORT_INSTRUMENT),
            shortcut=self._shortcuts.display(ShortcutId.IMPORT_INSTRUMENT),
            callback=lambda: self.call(self._panel.on_import_instrument_requested),
        )

    def add_action_items(self, target: VoiceSelection) -> None:
        """Builds every action a voice offers, in the order each menu prints them.

        The panel states its actions once, and whoever asks for them decides where they are shown:
        the row menu asks for the voice a pointer landed on, and the menu bar asks for the one the
        selection holds. An action added here reaches both, printing the key it answers to.
        """
        dpg.add_menu_item(
            label=self._label(SequencerVoicesElements.CONTEXT_EDIT),
            callback=lambda: self.call(self._panel.on_sample_edit_requested, target.voice_id),
        )
        dpg.add_menu_item(
            label=self._label(SequencerVoicesElements.CONTEXT_RENAME),
            shortcut=self._shortcuts.display(ShortcutId.VOICES_RENAME_VOICE),
            callback=lambda: self._panel.start_rename(target.voice_id),
        )
        dpg.add_menu_item(
            label=self._label(SequencerVoicesElements.CONTEXT_DUPLICATE),
            callback=lambda: self.call(self._panel.on_duplicate_requested, target.voice_id),
        )
        self._add_instrument_from_items(target)
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._label(SequencerVoicesElements.CONTEXT_REMOVE),
            shortcut=self._shortcuts.display(ShortcutId.VOICES_REMOVE_VOICE),
            callback=lambda: self.call(self._panel.on_remove_requested, target.voice_id),
        )
        dpg.add_separator()
        for move in VOICE_MOVES:
            self._add_move_item(move, target)

        dpg.add_separator()
        self._add_export_items(target)

    def _add_instrument_from_items(self, target: VoiceSelection) -> None:
        """Offers the channels of the voice a new instrument can be written from.

        A recording's channel carries frames of its own, so each of them makes a voice the reader
        can edit as envelopes. The channel names what the new instrument plays, so it is always the
        submenu that says which one, however few of them the voice offers. A voice that is already
        a set of envelopes offers the item unreachable, which says the action exists while leaving
        it where it belongs.
        """
        label = self._label(SequencerVoicesElements.CONTEXT_INSTRUMENT_FROM)
        channels = self.query(self._panel.instrument_channels, target.voice_id, default=NO_CHANNELS)
        if not channels:
            dpg.add_menu_item(label=label, enabled=False)
            return

        with dpg.menu(label=label):
            for channel_name in channels:
                self._add_instrument_from_channel_item(target, channel_name)

    def _add_instrument_from_channel_item(
        self,
        target: VoiceSelection,
        channel_name: ChannelName,
    ) -> None:
        dpg.add_menu_item(
            label=channel_label(self._language_manager, channel_name),
            callback=lambda: self.call(
                self._panel.on_instrument_from_channel_requested,
                target.voice_id,
                channel_name,
            ),
        )

    def _add_export_items(self, target: VoiceSelection) -> None:
        """Offers the instruments the voice would be written as, however many of them it holds.

        The menu asks how many instruments the voice contains rather than which kind of voice it
        is, so one item stands where there is nothing to choose and a channel submenu stands where
        a reader picks between slices. A voice writing nothing offers the item unreachable, which
        says an export exists without pretending this voice has one.
        """
        label = self._label(SequencerVoicesElements.CONTEXT_EXPORT_INSTRUMENT)
        channels = self.query(self._panel.voice_instruments, target.voice_id, default=NO_INSTRUMENTS)
        if not channels:
            dpg.add_menu_item(label=label, enabled=False)
            return

        if len(channels) > 1:
            with dpg.menu(label=label):
                for channel_name in channels:
                    self._add_export_channel_item(target, channel_name)

            return

        dpg.add_menu_item(
            label=label,
            callback=lambda: self._request_export(target.voice_id, channels[0]),
        )

    def _add_export_channel_item(
        self,
        target: VoiceSelection,
        channel_name: Optional[ChannelName],
    ) -> None:
        """Offers one of a voice's instruments, under the name that instrument carries."""
        dpg.add_menu_item(
            label=self._instrument_label(target, channel_name),
            callback=lambda: self._request_export(
                target.voice_id,
                channel_name,
            ),
        )

    def _instrument_label(
        self,
        target: VoiceSelection,
        channel_name: Optional[ChannelName],
    ) -> str:
        """The name one of a voice's instruments is listed under.

        A slice is named by the channel it was reconstructed for, which is what tells a voice's
        slices apart; an instrument stated for every channel alike is named after the voice.
        """
        if channel_name is None:
            return target.name

        return channel_label(self._language_manager, channel_name)

    def _request_export(
        self,
        voice_id: str,
        channel_name: Optional[ChannelName],
    ) -> None:
        self.call(
            self._panel.on_export_instrument_requested,
            voice_id,
            channel_name,
        )

    def _add_move_item(
        self,
        move: VoiceMove,
        target: VoiceSelection,
    ) -> None:
        """Builds one move item, offered while the move carries the voice somewhere new."""
        position = move.direction.target(target.position, self._panel.voice_count)
        dpg.add_menu_item(
            label=self._label(move.element),
            shortcut=self._shortcuts.display(move.shortcut),
            enabled=position is not None,
            callback=lambda: self.call(
                self._panel.on_move_requested,
                target.voice_id,
                position,
            ),
        )

    def _footprint_items(
        self,
        voice_id: str,
    ) -> List[Tuple[str, str]]:
        """The byte figures the menu prints for a sample: its total, then each channel that plays.

        The figures are asked for as the menu opens, so they name what the sample occupies at the
        moment a reader looks. A channel standing by is written by no export, so it costs nothing
        and the menu names the channels that do.
        """
        footprint = self.query(
            self._panel.sample_footprint,
            voice_id,
            default=None,
        )
        if footprint is None:
            return []

        items = [(self._lbl_sample_size, self._format_size(footprint.total_bytes))]
        for channel_name in ChannelName.items():
            instrument_bytes = footprint.bytes_for(channel_name)
            if instrument_bytes is not None:
                items.append(
                    (
                        channel_label(self._language_manager, channel_name),
                        self._format_size(instrument_bytes),
                    )
                )

        return items

    def _format_size(self, byte_count: int) -> str:
        return self._tpl_size_bytes.format(bytes=byte_count)

    def _label(self, element: SequencerVoicesElements) -> str:
        return self._language_manager[
            Page.SEQUENCER,
            Panel.VOICES,
            TextType.LABEL,
            element,
        ]
