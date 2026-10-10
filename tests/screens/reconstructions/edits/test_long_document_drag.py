import json
import os
import time
from pathlib import Path
from typing import Dict, Final, List, Tuple

import pytest

from automation.application.startup import Startup
from automation.environment import ARTIFACTS_VARIABLE
from automation.screen import Screen
from automation.steps.reconstructions import expect_open, leave_letting_it_go
from automation.vocabulary.graphs import WAVEFORM_REGENERATING
from automation.worlds.home import World
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.worlds.recordings import LONG_RECONSTRUCTION, long_document_world

DRAGGED_ITEMS: Final[Tuple[int, ...]] = (2, 4, 6, 8)
QUIET: Final[float] = 2.0
LOUD: Final[float] = 13.0
NEAR_THE_START: Final[float] = 0.05
ZOOM_NOTCHES: Final[int] = 5
LONG_GAP_SECONDS: Final[float] = 0.1
DRAIN_TIMEOUT_SECONDS: Final[float] = 120.0
READINGS_FILE: Final[str] = "frame_gaps.json"


def _frame_readings(stamps: List[float], last_release: float) -> Dict[str, float]:
    """What the clock said after every frame, read as the gaps between frames and the frames a second."""
    gaps = [later - earlier for earlier, later in zip(stamps, stamps[1:])]
    span = stamps[-1] - stamps[0]
    return {
        "frames": len(stamps),
        "seconds": span,
        "longest_gap_seconds": max(gaps),
        "gaps_over_a_tenth": sum(1 for gap in gaps if gap > LONG_GAP_SECONDS),
        "frames_per_second": (len(stamps) - 1) / span,
        "drain_seconds_after_the_last_release": stamps[-1] - last_release,
    }


class TestADragOnALongDocument:
    """How the frames keep coming while envelope bars of a two-minute document are dragged.

    The scenario records the clock after every frame through a burst of drags and until the
    waveform's fade ends, then keeps the longest gap between two frames, how many gaps ran over a
    tenth of a second, the frames drawn a second, and how long the line took to empty after the
    last release, beside the scenario's other files. It holds the application to nothing: the
    readings are what a change to the edit path is judged by, taken before and after the change.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds the two-minute reconstruction with its recording."""
        return long_document_world()

    @pytest.fixture
    def startup(self) -> Startup:
        """The two-minute reconstruction is open at start, with no project."""
        return Startup(reconstruction=LONG_RECONSTRUCTION, project=None)

    def test_the_frames_through_a_burst_of_drags(self, screen: Screen) -> None:
        """The readings are kept; the application is only asked to keep drawing and to leave cleanly."""
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        busy = screen.words(WAVEFORM_REGENERATING)
        stamps: List[float] = []
        releases: List[float] = []

        def open_and_zoom_in(screen: Screen) -> None:
            expect_open(screen, LONG_RECONSTRUCTION)
            instruments.bring_forward(ChannelName.PULSE1)
            screen.hand.scroll_into_view(graph.plot)
            graph.zoom_in(NEAR_THE_START, ZOOM_NOTCHES)

        def drag_until_the_line_empties(screen: Screen) -> None:
            standing = instruments.envelope_items(ChannelName.PULSE1, FeatureKey.VOLUME)
            with screen.record(time.monotonic) as recording:
                for turn, item in enumerate(DRAGGED_ITEMS):
                    graph.drag_item(item, start=standing[item], end=QUIET if turn % 2 == 0 else LOUD)
                    releases.append(time.monotonic())

                screen.bridge.expect(
                    screen.status,
                    busy.__ne__,
                    description="the line empty",
                    timeout=DRAIN_TIMEOUT_SECONDS,
                )

            stamps.extend(recording.values())

        def keep_the_readings(screen: Screen) -> None:
            readings = _frame_readings(stamps, releases[-1])
            print(json.dumps(readings))
            (Path(os.environ[ARTIFACTS_VARIABLE]) / READINGS_FILE).write_text(json.dumps(readings, indent=2))

        screen.scenario(open_and_zoom_in, drag_until_the_line_empties, keep_the_readings, leave_letting_it_go).run()
