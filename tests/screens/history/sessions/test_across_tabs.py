from typing import Dict, Final, List

from automation.screen import Screen
from automation.steps.sequencer import leave_letting_the_project_go, open_voice
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.history.constants import LEAD, PAD
from tests.screens.history.steps import (
    expect_lines,
    expect_reading,
    history_count,
    leading,
    press_on_the_sequencer,
    typed_values,
    volume_fields,
)

LEAD_TYPED: Final[Dict[ChannelName, str]] = {ChannelName.PULSE1: "8 3"}
PAD_TYPED: Final[Dict[ChannelName, str]] = {ChannelName.PULSE1: "10 5 1"}
CHANNELS: Final = (ChannelName.PULSE1,)
TRACKER_ROW: Final[int] = 1
TRACKER_VOLUME: Final[str] = "7"


class TestEditsAcrossBothTabs:
    """A sample's edit, a tracker cell and an instrument's edit undo in turn from the Sequencer and come back.

    Lead's volume is typed, then a tracker volume, then Pad's volume, each adding one line. Undo from the
    Sequencer takes Pad's edit back while Pad stands open, then the tracker cell, then Lead's edit, which
    reopening Lead shows. Three redos bring all three back, read in the tracker and in each reopened voice.
    """

    def test_each_edit_comes_back_where_it_was_made(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        instruments = screen.reconstructions.instruments
        standing: Dict[str, object] = {}
        lines: List[int] = []

        def open_on_the_tab(
            screen: Screen,
            name: str,
        ) -> None:
            open_voice(screen, name)
            screen.expect(screen.tabs.front, Tab.RECONSTRUCTIONS.__eq__, description=f"{name} open")

        def type_into(
            screen: Screen,
            typed: Dict[ChannelName, str],
        ) -> None:
            for channel, sequence in typed.items():
                instruments.type_envelope(channel, FeatureKey.VOLUME, sequence)

            expect_reading(
                screen,
                lambda: leading(volume_fields(screen, CHANNELS), typed),
                typed_values(typed),
                "the volume as typed",
            )

        def tracker_volume() -> str:
            return tracker.label(TRACKER_ROW, ChannelName.PULSE1, SubColumn.VOLUME)

        def edit_on_both_tabs(screen: Screen) -> None:
            lines.append(history_count(screen))
            open_on_the_tab(screen, LEAD)
            standing[LEAD] = volume_fields(screen, CHANNELS)
            type_into(screen, LEAD_TYPED)
            expect_lines(screen, lines[0] + 1)

            screen.tabs.bring_to_front(Tab.SEQUENCER)
            standing["tracker"] = tracker_volume()
            tracker.click(TRACKER_ROW, ChannelName.PULSE1, SubColumn.VOLUME)
            screen.hand.type_text(TRACKER_VOLUME)
            expect_lines(screen, lines[0] + 2)

            open_on_the_tab(screen, PAD)
            standing[PAD] = volume_fields(screen, CHANNELS)
            type_into(screen, PAD_TYPED)
            expect_lines(screen, lines[0] + 3)

        def undo_in_turn(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.UNDO)
            expect_reading(screen, lambda: volume_fields(screen, CHANNELS), standing[PAD], "Pad as it stood")

            press_on_the_sequencer(screen, ShortcutId.UNDO)
            expect_reading(screen, tracker_volume, standing["tracker"], "the tracker cell as it stood")

            press_on_the_sequencer(screen, ShortcutId.UNDO)
            open_on_the_tab(screen, LEAD)
            expect_reading(screen, lambda: volume_fields(screen, CHANNELS), standing[LEAD], "Lead as it stood")

        def redo_in_turn(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.REDO)
            expect_reading(
                screen,
                lambda: leading(volume_fields(screen, CHANNELS), LEAD_TYPED),
                typed_values(LEAD_TYPED),
                "Lead as typed",
            )

            press_on_the_sequencer(screen, ShortcutId.REDO)
            expect_reading(screen, tracker_volume, TRACKER_VOLUME, "the tracker cell as typed")

            press_on_the_sequencer(screen, ShortcutId.REDO)
            open_on_the_tab(screen, PAD)
            expect_reading(
                screen,
                lambda: leading(volume_fields(screen, CHANNELS), PAD_TYPED),
                typed_values(PAD_TYPED),
                "Pad as typed",
            )

        screen.scenario(edit_on_both_tabs, undo_in_turn, redo_in_turn, leave_letting_the_project_go).run()
