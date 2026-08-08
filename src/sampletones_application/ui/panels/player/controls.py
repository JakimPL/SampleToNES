import dearpygui.dearpygui as dpg

from sampletones_application.layout.glyphs.player import PlayerGlyphs
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.primitives import Dimensions
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.player import SUF_PLAYER_TOOLTIP
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.themes.theme import Theme
from sampletones_shared.types.callback import VoidCallback


def create_compact_transport_controls(
    parent: str,
    *,
    layout: PlayerLayout,
    glyphs: PlayerGlyphs,
    button_theme: Theme,
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
    """
    Render the three transport buttons as a compact fixed-width row inside ``parent``.
    """
    with dpg.group(
        horizontal=True,
        parent=parent,
    ):
        dpg.add_spacer(width=layout.toolbar.padding)
        _create_icon_button(
            play_tag,
            glyphs.play,
            play_tooltip,
            on_play,
            layout.button,
            button_theme,
        )
        dpg.add_spacer(width=layout.toolbar.gap)
        _create_icon_button(
            pause_tag,
            glyphs.pause,
            pause_tooltip,
            on_pause_or_resume,
            layout.button,
            button_theme,
        )
        dpg.add_spacer(width=layout.toolbar.gap)
        _create_icon_button(
            stop_tag,
            glyphs.stop,
            stop_tooltip,
            on_stop,
            layout.button,
            button_theme,
        )
        dpg.add_spacer(width=layout.toolbar.padding)


def _create_icon_button(
    tag: str,
    glyph: str,
    tooltip: str,
    callback: VoidCallback,
    button_layout: Dimensions,
    button_theme: Theme,
) -> None:
    GUIButton(
        tag=tag,
        label=glyph,
        callback=callback,
        enabled=False,
        font=Font.ICON,
        theme=button_theme,
        width=button_layout.width,
        height=button_layout.height,
    )
    with dpg.tooltip(parent=compose_tag(tag, SUF_BUTTON)):
        dpg.add_text(tooltip, tag=compose_tag(tag, SUF_PLAYER_TOOLTIP))
