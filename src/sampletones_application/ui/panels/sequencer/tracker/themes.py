from typing import Dict, Optional

from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.ui.panels.sequencer.tracker.callbacks import ThemeKey
from sampletones_application.ui.themes.inline import (
    create_header_selectable_theme,
    create_label_selectable_theme,
    create_selectable_text_theme,
)
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.faded import FadedColor
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.voices import VoiceKind

UNBUILT_THEME: int = 0


class TrackerThemes:
    """The shades a tracker cell, header and row number wear, built once and chosen per cell.

    Every shade a cell can take exists in two forms — the full color and the dimmed one a silenced
    channel wears — so choosing between them is a lookup rather than a color computed at each
    bind. A row of another frame, standing beside the shown one, wears the dimmed color as a label
    that answers no pointer. Building them needs a DearPyGui context, which is why :meth:`create`
    stands apart from construction and is called once the panel's widget tree is being raised.
    """

    def __init__(self, layout: SequencerLayout) -> None:
        self._layout = layout
        self._subcolumn: Dict[ThemeKey, int] = {}
        self._muted_subcolumn: Dict[ThemeKey, int] = {}
        self._context_subcolumn: Dict[ThemeKey, int] = {}
        self._pending: int = UNBUILT_THEME
        self._header: int = UNBUILT_THEME
        self._muted_header: int = UNBUILT_THEME
        self._column_label: int = UNBUILT_THEME
        self._row_number: int = UNBUILT_THEME
        self._context_row_number: int = UNBUILT_THEME

    def create(self) -> None:
        """Builds every theme the grid binds, which a DearPyGui context has to stand behind."""
        self._create_subcolumn_themes()
        self._pending = create_selectable_text_theme(self._layout.colors.text.pending)
        self._create_header_themes()
        row = self._layout.colors.text.row
        self._row_number = create_selectable_text_theme(row)
        self._context_row_number = create_label_selectable_theme(self._dimmed(row))

    def _create_subcolumn_themes(self) -> None:
        """Builds every text theme a cell can wear, in its full and its dimmed color.

        The voice slot carries one theme per kind of voice it can name, beside the shade it takes
        while it names none, so the color of a cell reports what stands in it. Transpose and volume
        speak for themselves and take one each. The dimmed variant keeps the same hue at reduced
        alpha, so a silenced channel's values stay readable and editable while the others are
        worked on.
        """
        text = self._layout.colors.text
        theme_colors: Dict[ThemeKey, BaseColor] = {
            (SubColumn.VOICE, None): text.voice,
            (SubColumn.VOICE, VoiceKind.SAMPLE): text.sample,
            (SubColumn.VOICE, VoiceKind.INSTRUMENT): text.instrument,
            (SubColumn.TRANSPOSE, None): text.transpose,
            (SubColumn.VOLUME, None): text.volume,
        }
        for theme_key, color in theme_colors.items():
            self._subcolumn[theme_key] = create_selectable_text_theme(color)
            self._muted_subcolumn[theme_key] = create_selectable_text_theme(self._dimmed(color))
            self._context_subcolumn[theme_key] = create_label_selectable_theme(self._dimmed(color))

    def _dimmed(self, color: BaseColor) -> BaseColor:
        """The same hue at the reduced alpha a silenced channel and a row of another frame read in."""
        return FadedColor(color=color, fraction=self._layout.tracker.muted_text_fraction)

    def _create_header_themes(self) -> None:
        """Builds the two shades a channel's header label takes: audible and silenced.

        Both carry the header's own hover and press washes, so a label reads as the switch it is
        while its text color reports whether the channel sounds.
        """
        header = self._layout.colors.header
        self._header = create_header_selectable_theme(
            self._layout.colors.label,
            header.hovered,
            header.active,
        )
        self._muted_header = create_header_selectable_theme(
            self._layout.colors.muted.text,
            header.hovered,
            header.active,
        )
        self._column_label = create_label_selectable_theme(self._layout.colors.label)

    def cell(
        self,
        subcolumn: SubColumn,
        kind: Optional[VoiceKind],
        *,
        muted: bool,
    ) -> int:
        """The theme a cell wears: its slot's color, dimmed while its channel is silenced.

        A voice slot takes the color of the kind of voice standing in it, so a reader tells a
        sample from an instrument across the whole grid; a slot naming none takes the
        neutral shade the other slots' colors are read against.

        Args:
            subcolumn: The slot the cell stands in.
            kind: The kind of voice the slot names, ``None`` where it names none.
            muted: Whether the cell's channel is silenced.

        Returns:
            int: The theme to bind.
        """
        themes = self._muted_subcolumn if muted else self._subcolumn
        return themes[(subcolumn, kind)]

    @property
    def pending(self) -> int:
        """The theme a cell wears while an entry is being typed into it: the plain text color, whatever the channel."""
        return self._pending

    def context_cell(self, subcolumn: SubColumn, kind: Optional[VoiceKind]) -> int:
        """The theme a cell of another frame's row wears: its slot's color, dimmed, as a plain label."""
        return self._context_subcolumn[(subcolumn, kind)]

    def header(self, *, muted: bool) -> int:
        """The theme a column header wears, which reports whether its channel sounds."""
        return self._muted_header if muted else self._header

    @property
    def column_label(self) -> int:
        """The theme a column's own label wears."""
        return self._column_label

    @property
    def row_number(self) -> int:
        """The theme the row-number column wears."""
        return self._row_number

    @property
    def context_row_number(self) -> int:
        """The theme a row number of another frame's row wears, dimmed as a plain label."""
        return self._context_row_number
