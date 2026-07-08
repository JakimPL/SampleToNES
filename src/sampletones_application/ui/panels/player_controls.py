from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import SUF_BUTTON
from sampletones_application.constants.player import (
    GLYPH_PLAYER_PAUSE,
    GLYPH_PLAYER_PLAY,
    GLYPH_PLAYER_STOP,
    SUF_PLAYER_TOOLTIP,
)
from sampletones_application.layout.player import PlayerButtonLayout, PlayerLayout
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_shared.types.callback import VoidCallback


def create_transport_controls(
    parent: str,
    *,
    layout: PlayerLayout,
    play_tag: str,
    pause_tag: str,
    stop_tag: str,
    play_tooltip: str,
    pause_tooltip: str,
    stop_tooltip: str,
    on_play: VoidCallback,
    on_pause_or_resume: VoidCallback,
    on_stop: VoidCallback,
    trailing: Optional[Callable[[], None]] = None,
) -> None:
    """Render the three transport buttons as centred icon glyphs inside ``parent``.

    Both audio players share this row. ``trailing`` builds an extra right-aligned
    widget (the sequencer's follow-playback checkbox) in a column after the buttons.
    """
    button = layout.button
    with dpg.table(
        header_row=False,
        policy=dpg.mvTable_SizingStretchProp,
        resizable=False,
        parent=parent,
    ):
        dpg.add_table_column()
        dpg.add_table_column(width_fixed=True, init_width_or_weight=button.width)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=button.gap)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=button.width)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=button.gap)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=button.width)
        dpg.add_table_column()
        if trailing is not None:
            dpg.add_table_column(width_fixed=True)

        with dpg.table_row():
            dpg.add_spacer()
            _create_icon_button(play_tag, GLYPH_PLAYER_PLAY, play_tooltip, on_play, button)
            dpg.add_spacer()
            _create_icon_button(pause_tag, GLYPH_PLAYER_PAUSE, pause_tooltip, on_pause_or_resume, button)
            dpg.add_spacer()
            _create_icon_button(stop_tag, GLYPH_PLAYER_STOP, stop_tooltip, on_stop, button)
            dpg.add_spacer()
            if trailing is not None:
                trailing()


def _create_icon_button(
    tag: str,
    glyph: str,
    tooltip: str,
    callback: VoidCallback,
    button_layout: PlayerButtonLayout,
) -> None:
    GUIButton(
        tag=tag,
        label=glyph,
        callback=callback,
        enabled=False,
        font=Font.ICON,
        width=-1,
        height=button_layout.height,
    )
    with dpg.tooltip(parent=f"{tag}{SUF_BUTTON}"):
        dpg.add_text(tooltip, tag=f"{tag}{SUF_PLAYER_TOOLTIP}")
