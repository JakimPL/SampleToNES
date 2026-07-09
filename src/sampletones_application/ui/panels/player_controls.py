from contextlib import contextmanager
from typing import Iterator

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import SUF_BUTTON
from sampletones_application.constants.player import SUF_PLAYER_TOOLTIP
from sampletones_application.layout.glyphs import PlayerGlyphs
from sampletones_application.layout.player import PlayerButtonLayout, PlayerLayout
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_shared.types.callback import VoidCallback


@contextmanager
def centered_card(parent: str, table_tag: str, card_tag: str, width: int) -> Iterator[str]:
    """Open a fixed-width bordered card horizontally centred within ``parent``.

    A transparent stretch table keeps a fixed-width column between two stretch
    columns, so the card sits centred whatever the parent's width. Content added
    inside the ``with`` block lands in the card; the caller binds the card theme.
    """
    with dpg.table(
        tag=table_tag,
        parent=parent,
        header_row=False,
        policy=dpg.mvTable_SizingStretchProp,
        resizable=False,
        width=-1,
    ):
        dpg.add_table_column()
        dpg.add_table_column(width_fixed=True, init_width_or_weight=width)
        dpg.add_table_column()

        with dpg.table_row():
            dpg.add_spacer()
            with dpg.child_window(
                tag=card_tag,
                width=-1,
                auto_resize_y=True,
                border=True,
                no_scrollbar=True,
                no_scroll_with_mouse=True,
            ):
                yield card_tag
            dpg.add_spacer()


def create_transport_controls(
    parent: str,
    *,
    layout: PlayerLayout,
    glyphs: PlayerGlyphs,
    play_tag: str,
    pause_tag: str,
    stop_tag: str,
    play_tooltip: str,
    pause_tooltip: str,
    stop_tooltip: str,
    on_play: VoidCallback,
    on_pause_or_resume: VoidCallback,
    on_stop: VoidCallback,
) -> None:
    """Render the three transport buttons as centred icon glyphs inside ``parent``."""
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

        with dpg.table_row():
            dpg.add_spacer()
            _create_icon_button(play_tag, glyphs.play, play_tooltip, on_play, button)
            dpg.add_spacer()
            _create_icon_button(pause_tag, glyphs.pause, pause_tooltip, on_pause_or_resume, button)
            dpg.add_spacer()
            _create_icon_button(stop_tag, glyphs.stop, stop_tooltip, on_stop, button)
            dpg.add_spacer()


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
