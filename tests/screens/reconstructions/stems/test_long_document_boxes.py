import time
from typing import Dict, Final, List, Optional

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.exports import leaving_asks_nothing
from automation.steps.reconstructions import expect_open, reconstruction_shade, wait_for_the_fade_to_end
from automation.worlds.home import World
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.readings import expect_no_long_hold, frame_readings, keep_readings, longest_gap_after_each
from tests.suite.screens.worlds.recordings import LONG_RECONSTRUCTION, alternating_document_world

TOGGLED_CHANNEL: Final[ChannelName] = ChannelName.NOISE
RECORDING_KEY: Final[str] = "0"
TICKS_PER_BOX: Final[int] = 2
FRAMES_AFTER_A_TICK: Final[int] = 5
BOX_READINGS: Final[str] = "frame_gaps_boxes.json"


@pytest.fixture(name="world")
def world_fixture() -> World:
    """The home holds the two-minute reconstruction over three recordings taking turns."""
    return alternating_document_world()


@pytest.fixture(name="startup")
def startup_fixture() -> Startup:
    """The two-minute reconstruction is open at start, with no project."""
    return Startup(reconstruction=LONG_RECONSTRUCTION, project=None)


class TestTheBoxesOnALongDocument:
    """How the frames keep coming while a channel's box above the waveform and a recording's box on the
    stems card are ticked off and on again on a two-minute document over three recordings taking turns.

    A box changes what is heard, so the waveform, the audio, the figures and the stretches every
    surface paints are read again from the document, and a sound the screen holds none of yet is
    rendered on the worker while the frames keep coming. The recordings take four-frame turns, so
    every lane divides into as many stretches as a long conversion over competing recordings does.
    The scenario records the clock after every frame through the ticks, each followed by the fade's
    end, and keeps the longest gap after each tick beside the readings the drag scenarios keep. The
    readings are what a change to the listening path is judged by, taken before and after the
    change; the one promise is relative: a tick holds a frame for a few of the machine's own
    frames at most.
    """

    def test_the_frames_through_the_ticks(self, screen: Screen) -> None:
        """The readings are kept and held to the machine's frame cadence; the application leaves cleanly."""
        reconstructions = screen.reconstructions
        stamps: List[float] = []
        ticks: List[float] = []
        unfaded: List[Optional[str]] = []

        def open_it(screen: Screen) -> None:
            expect_open(screen, LONG_RECONSTRUCTION)
            unfaded.append(reconstruction_shade(screen))

        def tick_the_boxes(screen: Screen) -> None:
            with screen.record(time.monotonic) as recording:
                for _ in range(TICKS_PER_BOX):
                    ticks.append(time.monotonic())
                    reconstructions.tick_channel(TOGGLED_CHANNEL)
                    wait_for_the_fade_to_end(screen, unfaded[0])
                    screen.frames(FRAMES_AFTER_A_TICK)

                for _ in range(TICKS_PER_BOX):
                    ticks.append(time.monotonic())
                    reconstructions.stems.tick(RECORDING_KEY)
                    wait_for_the_fade_to_end(screen, unfaded[0])
                    screen.frames(FRAMES_AFTER_A_TICK)

            stamps.extend(recording.values())

        def keep_the_readings(screen: Screen) -> None:
            frames = frame_readings(stamps, ticks[-1])
            readings: Dict[str, object] = dict(frames)
            readings["longest_gap_after_each_tick_seconds"] = longest_gap_after_each(stamps, ticks)
            keep_readings(BOX_READINGS, readings)
            expect_no_long_hold(frames)

        screen.scenario(open_it, tick_the_boxes, keep_the_readings, leaving_asks_nothing).run()
