import operator
from functools import partial
from typing import Final, Optional, Tuple

from automation.dearpygui.geometry import Rect
from automation.dearpygui.items.reading import read_item
from automation.dearpygui.keys import IMGUI_ESCAPE
from automation.palettes import shipped_palettes
from automation.screen import Screen
from automation.steps.sequencer import leave_letting_the_project_go
from automation.views.tracker import tracker_cell
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import MAX_CHANNEL_VALUE, composite, contrast_ratio
from tests.suite.screens.worlds.songs import PAD_ROW

FILLED_FLOOR: Final[float] = 4.5
STACKED_FLOOR: Final[float] = 3.5
DIM_FLOOR: Final[float] = 3.0
BAR_ROW: Final[int] = 0
PLAIN_ROW: Final[int] = 1
TYPED_ROW: Final[int] = 2
HOVERED_ROW: Final[int] = 3
LINE_NUMBER: Final[str] = "00"
PAD_NUMBER: Final[str] = "02"
TYPED_DIGIT: Final[str] = "0"
TYPING_FRAMES: Final[int] = 10
SETTLING_FRAMES: Final[int] = 6
INSET: Final[int] = 2

Color = Tuple[float, ...]


def in_steps(color: Color) -> ColorRGBA:
    """A color DearPyGui holds in fractions, in the whole steps the contrast arithmetic takes."""
    red, green, blue, alpha = (round(part * MAX_CHANNEL_VALUE) for part in color)
    return (red, green, blue, alpha)


class TestEveryKindReadsOnEveryBackground:
    """Every kind of text the tracker draws keeps a readable contrast against every background it can land on, in
    every palette: plain, beat and bar rows, the cursor's row and cell, a selected block, a hovered slot, and a
    muted channel.

    A filled voice, a transpose, a volume and the digit being typed are held to 4.5:1 on any row and under one
    wash on a plain row: the cursor's, a selection's or the pointer's; 3.5:1 where such a wash stacks on a
    beat or bar row. A placeholder and a muted channel's value are held to 3:1 on a plain row. The background is read from the
    frame's own pixels beside the text, and the text color from the slot's theme, so the figure is the one a
    reader sees. The scenario walks the default palette and then every shipped palette through Display
    settings.
    """

    def test_contrast_holds_in_every_palette(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        settings = screen.display_settings
        catalog = shipped_palettes()

        def slot_box(row: int, channel: ChannelName, slot: SubColumn) -> Rect:
            rect: Optional[Rect] = screen.bridge.ask(lambda: read_item(tracker_cell(row, channel, slot)).rect)
            assert rect is not None
            return rect

        def contrast(row: int, channel: ChannelName, slot: SubColumn) -> float:
            """The contrast of a slot's text, as drawn over the background inside the slot's top left corner.

            A muted channel's text is translucent, so the text is laid over the background first and the
            color that reaches the screen is what is held against it.
            """
            screen.frames(SETTLING_FRAMES)
            box = slot_box(row, channel, slot)
            pixels = screen.frame_pixels()
            background = in_steps(tuple(float(part) for part in pixels[int(box.y) + INSET, int(box.x) + INSET]))
            text = tracker.text_color(row, channel, slot)
            assert text is not None
            return contrast_ratio(composite(background, in_steps(text)), background)

        def expect_at_least(floor: float, row: int, channel: ChannelName, slot: SubColumn) -> None:
            ratio = contrast(row, channel, slot)
            assert ratio >= floor, f"{slot} at row {row} of {channel} reads at {ratio:.2f}, under {floor}"

        def readable_in(palette: str) -> None:
            """Reads every kind on every background in the palette now worn, leaving the grid as it found it."""
            expect_at_least(DIM_FLOOR, PLAIN_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            expect_at_least(FILLED_FLOOR, PLAIN_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE)
            expect_at_least(FILLED_FLOOR, PLAIN_ROW, ChannelName.PULSE1, SubColumn.VOLUME)
            expect_at_least(FILLED_FLOOR, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            expect_at_least(FILLED_FLOOR, BAR_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            expect_at_least(FILLED_FLOOR, PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE)

            tracker.click(TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            screen.expect(
                lambda: tracker.has_caret(TYPED_ROW, ChannelName.PULSE1), bool, description=f"the caret in {palette}"
            )
            tracker.leave()
            expect_at_least(FILLED_FLOOR, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            expect_at_least(FILLED_FLOOR, TYPED_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE)

            screen.hand.type_text(TYPED_DIGIT)
            screen.frames(TYPING_FRAMES)
            screen.expect(
                partial(tracker.label, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE),
                operator.methodcaller("startswith", TYPED_DIGIT),
                description="the typed digit pending",
            )
            expect_at_least(FILLED_FLOOR, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])
            screen.expect(
                partial(tracker.label, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE),
                LINE_NUMBER.__eq__,
                description="the entry let go",
            )

            tracker.click(PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE)
            screen.expect(
                lambda: tracker.has_caret(PAD_ROW, ChannelName.PULSE2), bool, description="the caret on a beat row"
            )
            tracker.leave()
            expect_at_least(STACKED_FLOOR, PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE)

            tracker.click(BAR_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            tracker.shift_click(TYPED_ROW, ChannelName.PULSE2, SubColumn.VOLUME)
            tracker.leave()
            expect_at_least(STACKED_FLOOR, BAR_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            expect_at_least(FILLED_FLOOR, PLAIN_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE)
            expect_at_least(STACKED_FLOOR, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])

            tracker.hover(HOVERED_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE)
            expect_at_least(FILLED_FLOOR, HOVERED_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE)
            tracker.hover(BAR_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            expect_at_least(STACKED_FLOOR, BAR_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            tracker.leave()

            tracker.click_header(ChannelName.PULSE1)
            tracker.leave()
            expect_at_least(DIM_FLOOR, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            tracker.click_header(ChannelName.PULSE1)

        def a_voice_on_a_plain_row(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            tracker.click(TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE)
            screen.hand.type_text(LINE_NUMBER)
            screen.frames(TYPING_FRAMES)
            screen.expect(
                partial(tracker.label, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE),
                LINE_NUMBER.__eq__,
                description="the voice typed on a plain row",
            )
            tracker.leave()

        def the_default_palette_reads(screen: Screen) -> None:
            readable_in(DEFAULT_PALETTE_NAME)

        def every_other_palette_reads(screen: Screen) -> None:
            for name in catalog.names:
                if name == DEFAULT_PALETTE_NAME:
                    continue

                settings.open()
                screen.expect(settings.is_shown, bool, description="Display settings")
                settings.choose_palette(name)
                screen.frames(SETTLING_FRAMES)
                settings.confirm()
                screen.expect(settings.is_shown, operator.not_, description="Display settings closed")

                readable_in(name)

        screen.scenario(
            a_voice_on_a_plain_row,
            the_default_palette_reads,
            every_other_palette_reads,
            leave_letting_the_project_go,
        ).run()
