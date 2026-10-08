import operator
from typing import Dict, Final, List

from automation.holds.regeneration import RegenerationHold
from automation.screen import Screen
from automation.steps.sequencer import leave_letting_the_project_go, open_voice
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.history.constants import LEAD
from tests.screens.history.steps import (
    expect_lines,
    expect_reading,
    history_count,
    leading,
    press_on_the_sequencer,
    typed_values,
    volume_fields,
)

TYPED: Final[Dict[ChannelName, str]] = {ChannelName.PULSE1: "4 2"}
CHANNELS: Final = tuple(TYPED)
TAKEN_OUT: Final[str] = "1"
KEPT: Final[str] = "0"
RETUNED_RATE: Final[int] = 50


def open_lead(screen: Screen) -> None:
    open_voice(screen, LEAD)
    screen.expect(screen.tabs.front, Tab.RECONSTRUCTIONS.__eq__, description="Lead open")


class TestAnUndoWaitingForARebuild:
    """Undo pressed while a typed edit is still being rebuilt waits for it, undoes it, and Redo brings it back.

    Lead opens with its rebuilds held, a volume is typed, and Undo is pressed while the rebuild waits: the
    History card stays as it was. Once the rebuild goes, the edit lands and the undo takes it back, so the
    field reads as it stood under a line in force at the start; Redo brings the typed values back.
    """

    def test_the_undo_comes_after_the_edit(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
    ) -> None:
        readings: List[Dict[ChannelName, str]] = []
        lines: List[int] = []

        def type_while_held(screen: Screen) -> None:
            open_lead(screen)
            readings.append(volume_fields(screen, CHANNELS))
            lines.append(history_count(screen))

            screen.reconstructions.instruments.type_envelope(
                ChannelName.PULSE1, FeatureKey.VOLUME, TYPED[ChannelName.PULSE1]
            )

            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")

        def undo_while_held(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.UNDO)

            assert history_count(screen) == lines[0]

        def the_edit_lands_and_goes(screen: Screen) -> None:
            regeneration_hold.release()

            expect_lines(screen, lines[0] + 1)
            expect_reading(screen, lambda: volume_fields(screen, CHANNELS), readings[0], "the volume as it stood")
            assert screen.sequencer.history.lines()[-1].current

        def redo_brings_it_back(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.REDO)

            expect_reading(
                screen,
                lambda: leading(volume_fields(screen, CHANNELS), TYPED),
                typed_values(TYPED),
                "the volume as typed",
            )

        screen.scenario(
            type_while_held,
            undo_while_held,
            the_edit_lands_and_goes,
            redo_brings_it_back,
            leave_letting_the_project_go,
        ).run()


class TestARecordingTakenOut:
    """A recording taken out of a sample from the stems card comes back with Undo and leaves again with Redo.

    Lead opens and its second recording is removed at the question. Undo on the Sequencer lists it again
    beside the first, and Redo takes it out again while the first stays.
    """

    def test_undo_and_redo_reach_the_stems_card(self, screen: Screen) -> None:
        stems = screen.reconstructions.stems
        lines: List[int] = []

        def take_the_second_recording_out(screen: Screen) -> None:
            open_lead(screen)
            screen.expect(lambda: stems.has_row(TAKEN_OUT), bool, description="the second recording listed")
            lines.append(history_count(screen))

            stems.remove(TAKEN_OUT)
            screen.expect(stems.remove_prompt.is_shown, bool, description="the question about removing")
            stems.remove_prompt.confirm()

            screen.expect(lambda: stems.has_row(TAKEN_OUT), operator.not_, description="the second recording gone")
            expect_lines(screen, lines[0] + 1)

        def undo_lists_it_again(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.UNDO)

            screen.expect(lambda: stems.has_row(TAKEN_OUT), bool, description="the second recording back")
            assert stems.has_row(KEPT)

        def redo_takes_it_out_again(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.REDO)

            screen.expect(
                lambda: stems.has_row(TAKEN_OUT), operator.not_, description="the second recording gone again"
            )
            assert stems.has_row(KEPT)

        screen.scenario(
            take_the_second_recording_out,
            undo_lists_it_again,
            redo_takes_it_out_again,
            leave_letting_the_project_go,
        ).run()


class TestARateChangeWithASampleOpen:
    """A rate change confirmed while a sample stands open is one entry, which Undo and Redo move as a whole.

    Lead opens, and the Sequencer's NES frequency is retyped and confirmed at the question: one line joins
    the card. Undo brings the field back to the project's rate and Redo to the new one.
    """

    def test_one_entry_moves_the_rate(self, screen: Screen) -> None:
        module = screen.sequencer.module
        rates: List[int] = []
        lines: List[int] = []

        def retune_with_lead_open(screen: Screen) -> None:
            open_lead(screen)
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            rates.append(module.nes_frequency())
            lines.append(history_count(screen))

            module.retype_nes_frequency(RETUNED_RATE)
            screen.expect(module.retune_prompt.is_shown, bool, description="the question about retuning")
            module.retune_prompt.confirm()

            screen.expect(module.nes_frequency, RETUNED_RATE.__eq__, description="the new rate")
            expect_lines(screen, lines[0] + 1)

        def undo_restores_the_rate(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.UNDO)

            screen.expect(module.nes_frequency, rates[0].__eq__, description="the rate as it stood")
            assert history_count(screen) == lines[0] + 1

        def redo_retunes_again(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.REDO)

            screen.expect(module.nes_frequency, RETUNED_RATE.__eq__, description="the new rate again")

        screen.scenario(
            retune_with_lead_open,
            undo_restores_the_rate,
            redo_retunes_again,
            leave_letting_the_project_go,
        ).run()
