import math
import operator
from functools import partial
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.utils.display import BLANK
from tests.suite.screens.application import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import marked, raise_the_first_level, titled, voice_title
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, open_voice
from tests.suite.screens.world import ARRANGED_PROJECT, LINE

SETTLING_FRAMES: Final[int] = 20
EMPTY_VOICE: Final[str] = ".."
FIRST_PATTERN: Final[str] = "00"
SECOND_PATTERN: Final[str] = "01"
LINE_NUMBER: Final[str] = "00"
FIRST_HIGHLIGHT: Final[int] = 3
SECOND_HIGHLIGHT: Final[int] = 6
TINTED_ROWS_READ: Final[int] = 13
UNITY: Final[float] = 1.0
LOUDEST_GAIN: Final[float] = 2.0
BEYOND_THE_LEFT: Final[float] = -0.5
BEYOND_THE_RIGHT: Final[float] = 1.5
NEAR_THE_RIGHT: Final[float] = 0.97
FROM_THE_MIDDLE: Final[float] = 0.5
DECIBELS_PER_DOUBLING: Final[float] = 20.0
LINE_ORDINAL: Final[int] = 0
FIFTY_HERTZ: Final[int] = 50
SIXTY_HERTZ: Final[int] = 60
REFIT_TOLERANCE: Final[float] = 0.02
SILENT_GAIN: Final[str] = "settings.audio.message.master_gain_silent"
GAIN_TEMPLATE: Final[str] = "settings.audio.template.master_gain_db"
EVERY_CHANNEL: Final[Tuple[ChannelName, ...]] = tuple(ChannelName.items())
SAMPLE_COLUMN: Final[Optional[ChannelName]] = None


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


def on_the_sequencer(screen: Screen) -> None:
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.expect(screen.sequencer.voices.names, bool, description="the project's voices")


class TestTheOrderTable:
    """An order entry typed names the pattern a channel plays at that frame, and the tracker follows it."""

    def test_patterns_follow_the_order(self, screen: Screen) -> None:
        order = screen.sequencer.order
        tracker = screen.sequencer.tracker

        def a_new_pattern_number_shows_a_new_pattern(screen: Screen) -> None:
            on_the_sequencer(screen)
            assert order.label(ChannelName.PULSE1, 0) == FIRST_PATTERN
            order.click(ChannelName.PULSE1, 0)

            screen.hand.type_text(SECOND_PATTERN)

            screen.expect(partial(order.label, ChannelName.PULSE1, 0), SECOND_PATTERN.__eq__, description="pattern 01")
            assert tracker.label(0, ChannelName.PULSE1, SubColumn.VOICE) == EMPTY_VOICE

        def the_first_number_brings_the_line_back(screen: Screen) -> None:
            order.click(ChannelName.PULSE1, 0)

            screen.hand.type_text(FIRST_PATTERN)

            screen.expect(partial(order.label, ChannelName.PULSE1, 0), FIRST_PATTERN.__eq__, description="pattern 00")
            screen.expect(
                partial(tracker.label, 0, ChannelName.PULSE1, SubColumn.VOICE),
                LINE_NUMBER.__eq__,
                description="the line back",
            )

        screen.scenario(
            a_new_pattern_number_shows_a_new_pattern,
            the_first_number_brings_the_line_back,
            leave_letting_the_project_go,
        ).run()


class TestAVolumeWhereNoSamplePlays:
    """A volume typed in the Sample column of an empty frame keeps the cell, records nothing and makes no pattern."""

    def test_the_frame_stays_empty(self, screen: Screen) -> None:
        order = screen.sequencer.order
        tracker = screen.sequencer.tracker
        history = screen.sequencer.history
        before: List[int] = []

        def add_an_empty_frame(screen: Screen) -> None:
            on_the_sequencer(screen)
            order.click(ChannelName.PULSE1, 0)

            screen.press_shortcut(ShortcutId.ORDER_ADD_FRAME)

            screen.expect(order.positions, (2).__eq__, description="a second frame")
            assert [order.label(channel, 1) for channel in EVERY_CHANNEL] == [EMPTY_VOICE] * len(EVERY_CHANNEL)

        def type_a_volume_on_it(screen: Screen) -> None:
            order.click(ChannelName.PULSE1, 1)
            before.append(len(history.lines()))
            tracker.click(0, SAMPLE_COLUMN, SubColumn.VOLUME)

            screen.hand.type_text("5")

            screen.frames(SETTLING_FRAMES)
            assert tracker.label(0, SAMPLE_COLUMN, SubColumn.VOLUME) == BLANK
            assert len(history.lines()) == before[0]
            assert [order.label(channel, 1) for channel in EVERY_CHANNEL] == [EMPTY_VOICE] * len(EVERY_CHANNEL)

        screen.scenario(add_an_empty_frame, type_a_volume_on_it, leave_letting_the_project_go).run()


class TestTheHighlights:
    """The tracker tints the rows the project's highlights name, and those alone."""

    def test_rows_on_the_highlight_are_tinted(self, screen: Screen) -> None:
        properties = screen.project.properties
        tracker = screen.sequencer.tracker

        def set_highlights_of_three_and_six(screen: Screen) -> None:
            on_the_sequencer(screen)
            properties.open()
            screen.expect(properties.is_shown, bool, description="Project properties")

            properties.retype_highlights(FIRST_HIGHLIGHT, SECOND_HIGHLIGHT)
            properties.confirm()

            screen.expect(properties.is_shown, operator.not_, description="Project properties closed")

        def every_third_row_is_tinted(screen: Screen) -> None:
            expected = [row % FIRST_HIGHLIGHT == 0 for row in range(TINTED_ROWS_READ)]

            screen.expect(
                lambda: [tracker.is_row_tinted(row) for row in range(TINTED_ROWS_READ)],
                expected.__eq__,
                description="every third row tinted",
            )

        screen.scenario(set_highlights_of_three_and_six, every_third_row_is_tinted, leave_letting_the_project_go).run()


class TestTheMasterGain:
    """The decibel line follows the master gain: silence at the bottom, the level above unity in the warning color."""

    def test_the_line_follows_the_slider(self, screen: Screen) -> None:
        settings = screen.audio_settings
        unity_color: List[Tuple[float, ...]] = []

        def open_audio_settings(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.AUDIO_SETTINGS)
            screen.expect(settings.is_shown, bool, description="Audio settings")

            assert settings.gain() == UNITY
            unity_color.append(settings.decibels_color())

        def all_the_way_down_reads_silence(screen: Screen) -> None:
            settings.drag_gain(FROM_THE_MIDDLE, BEYOND_THE_LEFT)

            screen.expect(settings.gain, (0.0).__eq__, description="the gain at zero")
            assert settings.decibels() == screen.words(SILENT_GAIN)
            assert settings.decibels_color() == unity_color[0]

        def all_the_way_up_reads_the_level_in_warning(screen: Screen) -> None:
            settings.drag_gain(FROM_THE_MIDDLE, BEYOND_THE_RIGHT)

            screen.expect(settings.gain, LOUDEST_GAIN.__eq__, description="the gain at its top")
            level = DECIBELS_PER_DOUBLING * math.log10(LOUDEST_GAIN)
            assert settings.decibels() == screen.words(GAIN_TEMPLATE).format(decibels=level)
            assert settings.decibels_color() != unity_color[0]

        def back_to_unity(screen: Screen) -> None:
            settings.drag_gain(NEAR_THE_RIGHT, FROM_THE_MIDDLE)

            gain = screen.expect(settings.gain, lambda found: 0.0 < found < LOUDEST_GAIN, description="a middle gain")
            assert settings.decibels() == screen.words(GAIN_TEMPLATE).format(
                decibels=DECIBELS_PER_DOUBLING * math.log10(gain)
            )
            screen.press_shortcut(ShortcutId.DIALOG_CANCEL)
            screen.expect(settings.is_shown, operator.not_, description="Audio settings closed")

        screen.scenario(
            open_audio_settings,
            all_the_way_down_reads_silence,
            all_the_way_up_reads_the_level_in_warning,
            back_to_unity,
        ).run()


class TestRetuningWithASampleOpen:
    """A new NES frequency retunes the sample open on the Reconstructions tab: it re-fits, keeping the edit before.

    The edit is made on the noise, whose last frame is silent, so the sample keeps its frames and
    the waveform stretches by the ratio of the two rates.
    """

    def test_the_waveform_refits_and_the_edit_stays(self, screen: Screen) -> None:
        module = screen.sequencer.module
        reconstructions = screen.reconstructions
        typed: List[str] = []
        limits: List[Tuple[float, float]] = []

        def edit_the_line(screen: Screen) -> None:
            open_voice(screen, LINE)
            screen.expect(
                screen.title,
                voice_title(screen, ARRANGED_PROJECT.stem, LINE_ORDINAL, LINE, unsaved=False).__eq__,
                description="the line open",
            )

            typed.append(
                raise_the_first_level(
                    screen,
                    ChannelName.NOISE,
                    title=voice_title(screen, ARRANGED_PROJECT.stem, LINE_ORDINAL, LINE, unsaved=True),
                )
            )
            limits.append(reconstructions.waveform.limits())

        def retune_to_fifty(screen: Screen) -> None:
            on_the_sequencer(screen)
            assert module.nes_frequency() == SIXTY_HERTZ

            module.retype_nes_frequency(FIFTY_HERTZ)

            screen.expect(module.retune_prompt.is_shown, bool, description="the question about retuning")
            module.retune_prompt.confirm()
            screen.expect(module.retune_prompt.is_shown, operator.not_, description="the question answered")

        def the_waveform_refits_and_the_edit_stays(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
            low, high = limits[0]

            refitted = screen.expect(
                reconstructions.waveform.limits,
                lambda found: abs(found[1] / high - SIXTY_HERTZ / FIFTY_HERTZ) <= REFIT_TOLERANCE,
                description="the waveform re-fitted to the longer frames",
            )
            assert refitted[0] == low
            assert reconstructions.instruments.envelope(ChannelName.NOISE, FeatureKey.VOLUME) == typed[0]

        screen.scenario(
            edit_the_line, retune_to_fifty, the_waveform_refits_and_the_edit_stays, leave_letting_the_project_go
        ).run()


class TestSavingAProjectOpenedAtStart:
    """A project opened as the application starts is saved to its own file by Save, asking nothing."""

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a project opened at start is saved as though it had no file",
    )
    def test_save_writes_its_file(self, screen: Screen) -> None:
        on_the_sequencer(screen)
        screen.sequencer.tracker.click(1, ChannelName.PULSE2, SubColumn.VOICE)
        screen.hand.type_text(LINE_NUMBER)
        screen.expect(
            screen.title, titled(screen, marked(ARRANGED_PROJECT.stem, unsaved=True)).__eq__, description="changed"
        )

        screen.press_shortcut(ShortcutId.SAVE_PROJECT)

        screen.frames(SETTLING_FRAMES)
        assert screen.dialog_requests() == ()
        screen.expect(screen.project.saved_notice.is_shown, bool, description="the project saved notice")
