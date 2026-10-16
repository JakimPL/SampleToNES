import dataclasses
from pathlib import Path
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.boundaries.audio import SILENT_DEVICE_NAME
from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from automation.vocabulary.playback import PAUSE, PLAY
from automation.worlds.home import World
from sampletones_application.config.session.application.audio import AudioConfig
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.audio import CurrentDevice
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from tests.suite.screens.worlds.recordings import SHORT_RECONSTRUCTION, playing_world

DEVICE_RATE: Final[int] = 48000
SILENT_DEVICE_INDEX: Final[int] = 0
SILENT_HOST_API: Final[int] = 0
LENGTH_TOLERANCE: Final[float] = 0.01
RATE_LABEL: Final[str] = "settings.audio.template.sample_rate_label"


@pytest.fixture
def world() -> World:
    """The playing world, with the silent device set to play at :data:`DEVICE_RATE`."""
    device = CurrentDevice(
        device_index=SILENT_DEVICE_INDEX,
        name=SILENT_DEVICE_NAME,
        sample_rate=DEVICE_RATE,
        host_api=SILENT_HOST_API,
    )
    config = ApplicationConfig(audio=AudioConfig(current_device=device))
    return dataclasses.replace(playing_world(), application_config=config)


@pytest.fixture
def startup() -> Startup:
    """The application opens the short reconstruction at start."""
    return Startup(reconstruction=SHORT_RECONSTRUCTION, project=None)


def played_frames(path: Path) -> int:
    """The frames the reconstruction stored at ``path`` plays at the device's rate, from its own length."""
    document = Reconstruction.load(path)
    assert document.config.sample_rate != DEVICE_RATE, "the document plays at the device's rate already"
    samples = max(len(instructions) for instructions in document.instructions.values()) * document.config.frame_length
    return round(samples * DEVICE_RATE / document.config.sample_rate)


class TestADocumentAtAnotherRate:
    """A reconstruction made at one rate plays at its own length on a device playing at another.

    The device plays at :data:`DEVICE_RATE`, which Audio settings names before anything plays, and the
    reconstruction was made at a rate of its own. Play opens a stream at the device's rate, and the frames
    written to it by the end last as long as the reconstruction does.
    """

    def test_the_reconstruction_plays_at_its_own_length(self, screen: Screen) -> None:
        settings = screen.audio_settings

        def the_device_plays_at_its_rate(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.AUDIO_SETTINGS)
            screen.expect(settings.is_shown, bool, description="Audio settings")

            assert settings.sample_rate() == screen.words(RATE_LABEL).format(rate=DEVICE_RATE)

            screen.press_shortcut(ShortcutId.DIALOG_CANCEL)
            screen.expect(lambda: not settings.is_shown(), bool, description="Audio settings closed")

        def play_to_the_end(screen: Screen) -> None:
            expect_open(screen, SHORT_RECONSTRUCTION)
            screen.press_shortcut(ShortcutId.PLAY)

            screen.expect(screen.sequencer.playback.play_entry, screen.words(PAUSE).__eq__, description="playing")
            screen.expect(screen.sequencer.playback.play_entry, screen.words(PLAY).__eq__, description="played out")
            screen.expect(lambda: screen.output_streams()[-1].closed, bool, description="the stream closed")

        def it_lasted_its_own_length(screen: Screen) -> None:
            stream = screen.output_streams()[-1]
            expected = played_frames(SHORT_RECONSTRUCTION)

            assert stream.rate == DEVICE_RATE
            assert abs(stream.frames - expected) <= expected * LENGTH_TOLERANCE, (stream.frames, expected)

        screen.scenario(the_device_plays_at_its_rate, play_to_the_end, it_lasted_its_own_length).run()
