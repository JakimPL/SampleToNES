import operator
from pathlib import Path
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from automation.worlds.home import World
from tests.screens.reconstructions.player.constants import RECONSTRUCTION_LINE
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION, TAKES, playing_world

ORIGINAL_SWITCH: Final[str] = "reconstructions.reconstruction.label.original_audio_radio"
RECONSTRUCTION_SWITCH: Final[str] = "reconstructions.reconstruction.label.reconstruction_radio"
ORIGINAL_LINE: Final[str] = "global.graph.label.waveform_original"


class TestTheSourceSwitch:
    """The switch above the waveform puts the source it names on top of the waveform, and back."""

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_the_source_chosen_is_drawn_on_top(self, screen: Screen) -> None:
        """The reconstruction starts on top, the original takes the top when chosen, and the reconstruction
        again.
        """
        reconstructions = screen.reconstructions
        waveform = reconstructions.waveform
        original = waveform.series_tag(screen.words(ORIGINAL_LINE))
        reconstruction = waveform.series_tag(screen.words(RECONSTRUCTION_LINE))

        def the_reconstruction_on_top(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)

            assert reconstructions.audio_source() == screen.words(RECONSTRUCTION_SWITCH)
            assert waveform.series() == (original, reconstruction)

        def the_original_chosen(screen: Screen) -> None:
            reconstructions.choose_audio_source(screen.words(ORIGINAL_SWITCH))

            screen.expect(waveform.series, (reconstruction, original).__eq__, description="the original on top")

        def the_reconstruction_chosen_again(screen: Screen) -> None:
            reconstructions.choose_audio_source(screen.words(RECONSTRUCTION_SWITCH))

            screen.expect(waveform.series, (original, reconstruction).__eq__, description="the reconstruction on top")

        screen.scenario(the_reconstruction_on_top, the_original_chosen, the_reconstruction_chosen_again).run()


class TestTheSourceSwitchWithItsRecordingGone:
    """A reconstruction whose recording is gone offers the reconstruction alone.

    The home lacks the recording. Opening the reconstruction shows a notice naming the missing file; once
    dismissed, the switch offers no other source.
    """

    @pytest.fixture
    def world(self) -> World:
        """The Reconstructions home with the first recording's file removed."""
        world = playing_world()
        gone = Path.cwd() / TAKES[0]
        return World(
            state=world.state,
            application_config=world.application_config,
            config=world.config,
            files=tuple(file for file in world.files if not (isinstance(file, Recording) and file.destination == gone)),
        )

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_the_switch_stays_on_the_reconstruction(self, screen: Screen) -> None:
        """The notice names the missing recording, and the switch offers the reconstruction only."""
        reconstructions = screen.reconstructions
        notice = screen.file_not_found_notice

        def the_missing_recording_is_named(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            screen.expect(notice.is_shown, bool, description="the notice about the recording")

            assert str(Path.cwd() / TAKES[0]) in notice.words()
            notice.dismiss()
            screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")

        def the_switch_offers_nothing_else(screen: Screen) -> None:
            assert not reconstructions.can_choose_audio_source()
            assert reconstructions.audio_source() == screen.words(RECONSTRUCTION_SWITCH)

        screen.scenario(the_missing_recording_is_named, the_switch_offers_nothing_else).run()

    def test_the_waveform_draws_the_reconstruction_alone(self, screen: Screen) -> None:
        """The waveform shows one line, the reconstruction's."""
        waveform = screen.reconstructions.waveform
        notice = screen.file_not_found_notice
        expect_open(screen, PLAYABLE_RECONSTRUCTION)
        screen.expect(notice.is_shown, bool, description="the notice about the recording")
        notice.dismiss()
        screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")

        assert waveform.series() == (waveform.series_tag(screen.words(RECONSTRUCTION_LINE)),)
