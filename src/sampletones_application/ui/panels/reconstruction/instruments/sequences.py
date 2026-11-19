from functools import partial
from typing import Any, Callable, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_COPY,
    SUF_TEXT,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_INPUT_INVALID,
    TAG_GLOBAL_THEME_INPUT_WARNING,
)
from sampletones_application.tags.graphs import SUF_GRAPH_RAW_DATA
from sampletones_application.tags.reconstructions import TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.clipboard.copy_button import copy_to_clipboard
from sampletones_application.utils.gui.dpg import dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exports.ceilings import FormatShortening, format_shortenings
from sampletones_core.exports.format import ExportFormat
from sampletones_core.features import BEND_FEATURES
from sampletones_core.features.envelope import Envelope
from sampletones_core.features.text import format_envelope, parse_envelope
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.arrays import clamp
from sampletones_shared.utils.callbacks import CallbackMixin

OnSequenceTypedCallback = Callable[[ChannelName, FeatureKey, Envelope[int]], None]
SequenceInput = Tuple[ChannelName, FeatureKey, Tuple[int, int]]


def sequence_input_tag(channel_name: ChannelName, feature_key: FeatureKey) -> str:
    """The input holding the typed sequence of ``channel_name``'s ``feature_key`` dimension."""
    return compose_tag(_sequence_group_tag(channel_name, feature_key), SUF_TEXT)


def _sequence_group_tag(channel_name: ChannelName, feature_key: FeatureKey) -> str:
    return compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR, channel_name, feature_key, SUF_GRAPH_RAW_DATA)


class SequenceInputs(CallbackMixin):
    """The typed sequence beside each dimension's bars, which a reader reads, types and copies.

    An input shows its dimension as a reader would type it, takes a typed one in its place, and
    carries the warning color while a tracker export would hold only part of it. A typed sequence
    reaches ``on_typed`` once it is clamped to the values the dimension writes.
    """

    def __init__(
        self,
        *,
        copy_width: int,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._copy_width = copy_width
        self._language_manager = language_manager
        self._status_bar = status_bar
        self._sequences: Dict[Tuple[ChannelName, FeatureKey], Envelope[int]] = {}

        self._theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT)
        self._invalid_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_INPUT_INVALID)
        self._warning_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_INPUT_WARNING)
        self._lbl_copy = language_manager["reconstructions.instruments.label.copy_button"]

        self.on_typed: Optional[OnSequenceTypedCallback] = None

    def create(
        self,
        parent: str,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data_range: Tuple[int, int],
    ) -> None:
        """Builds one dimension's copy button and its input, empty until the dimension is written."""
        group_tag = _sequence_group_tag(channel_name, feature_key)
        input_tag = sequence_input_tag(channel_name, feature_key)
        copy_button_tag = compose_tag(group_tag, SUF_BUTTON_COPY)

        with dpg.group(tag=group_tag, parent=parent, horizontal=True):
            GUIButton(
                tag=copy_button_tag,
                label=self._lbl_copy,
                width=self._copy_width,
                callback=self.copy_callback(channel_name, feature_key, copy_button_tag),
            )

            dpg.add_input_text(
                tag=input_tag,
                default_value=format_envelope(Envelope[int]()),
                width=-1,
                multiline=False,
                on_enter=True,
                decimal=False,
                callback=self._on_typed,
                user_data=(channel_name, feature_key, data_range),
            )
            FontRegistry.bind_to_item(input_tag, Font.MONO)

        self._status_bar.bind_to_item(
            copy_button_tag,
            self._language_manager["reconstructions.instruments.message.status_copy_sequence"],
        )
        self._status_bar.bind_to_item(input_tag, partial(self.status_message, channel_name, feature_key))
        self._explain_bend(input_tag, feature_key)

    def standing(self, channel_name: ChannelName, feature_key: FeatureKey) -> Envelope[int]:
        """The dimension the input shows, which is what an edit of its values starts from."""
        return self._sequences.get((channel_name, feature_key), Envelope[int]())

    def write(self, channel_name: ChannelName, feature_key: FeatureKey, envelope: Envelope[int]) -> None:
        """Writes the dimension into its input, as a reader would type it."""
        dpg_set_value(sequence_input_tag(channel_name, feature_key), format_envelope(envelope))
        self.show(channel_name, feature_key, envelope)

    def show(self, channel_name: ChannelName, feature_key: FeatureKey, envelope: Envelope[int]) -> None:
        """Holds the dimension the input now shows, colored by how the tracker exports treat its length.

        A sequence any tracker export holds only part of carries the warning color, so which
        dimensions reach every file whole is visible before an export.
        """
        self._sequences[(channel_name, feature_key)] = envelope
        theme = self._warning_theme if format_shortenings(feature_key, envelope) else self._theme
        theme.bind_to_item(sequence_input_tag(channel_name, feature_key))

    def status_message(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        *_args: Any,
        **_kwargs: Any,
    ) -> str:
        """Describes the sequence input, naming what each tracker export keeps of an over-long one."""
        envelope = self.standing(channel_name, feature_key)
        shortenings = format_shortenings(feature_key, envelope)
        if shortenings:
            separator = self._language_manager["reconstructions.instruments.template.kept_separator"]
            return self._language_manager["reconstructions.instruments.message.status_sequence_too_long"].format(
                instrument_feature=feature_key.capitalized,
                items=len(envelope.items),
                kept=separator.join(self._kept_by(shortening) for shortening in shortenings),
            )

        return self._language_manager["reconstructions.instruments.message.status_sequence"].format(
            instrument_feature=feature_key.capitalized
        )

    def copy_callback(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        button_tag: str,
    ) -> VoidCallback:
        """The press handler for one dimension's copy button.

        The button stands beside its input from the moment the tab is built, so the press reads
        the dimension the input shows then, written out as a reader would type it.
        """
        return lambda: self._copy(format_envelope(self.standing(channel_name, feature_key)), button_tag)

    def _copy(self, text: str, button_tag: str) -> None:
        copy_to_clipboard(
            text,
            self._lbl_copy,
            button_tag,
            copied_label=self._language_manager["global.dialog.label.copied"],
        )

    def _kept_by(self, shortening: FormatShortening) -> str:
        """Names one tracker export beside the items it keeps of a dimension."""
        match shortening.export_format:
            case ExportFormat.FAMITRACKER:
                template = self._language_manager["reconstructions.instruments.template.kept_famitracker"]
            case ExportFormat.BITPHASE:
                template = self._language_manager["reconstructions.instruments.template.kept_bitphase"]
            case ExportFormat.BITPHASE_PRESET:
                template = self._language_manager["reconstructions.instruments.template.kept_bitphase_preset"]

        return template.format(limit=shortening.kept)

    def _explain_bend(self, input_tag: str, feature_key: FeatureKey) -> None:
        """Says what one item of a bend dimension is worth, since that follows the note it bends.

        A divider step spans well under a cent at the lowest notes and a whole semitone at the
        highest, so the axis a bend is drawn on states the range a sequence stores rather than the
        distance a value covers.
        """
        if feature_key not in BEND_FEATURES:
            return

        show_tooltip(
            input_tag,
            self._language_manager[
                (
                    "reconstructions.instruments.tooltip.hi_pitch_bend"
                    if feature_key is FeatureKey.HI_PITCH
                    else "reconstructions.instruments.tooltip.pitch_bend"
                )
            ],
        )

    def _on_typed(self, sender: Sender, app_data: str, user_data: SequenceInput) -> None:
        channel_name, feature_key, data_range = user_data
        try:
            typed = parse_envelope(app_data)
        except ValueError:
            logger.error(f"Invalid {channel_name.name} data input for {feature_key.name}: {app_data}")
            self._invalid_theme.bind_to_item(sender)
            return

        envelope = typed.with_items(tuple(clamp(item, *data_range) for item in typed.items))
        self.show(channel_name, feature_key, envelope)
        dpg.set_value(sender, format_envelope(envelope))
        self.call(self.on_typed, channel_name, feature_key, envelope)
