import json
import os
import time
from pathlib import Path
from typing import Dict, Final, List, Tuple

import pytest

from automation.application.startup import Startup
from automation.environment import ARTIFACTS_VARIABLE
from automation.holds.regeneration import RegenerationHold
from automation.screen import Screen
from automation.steps.reconstructions import expect_open, leave_letting_it_go
from automation.views.bar_graph import BarGraph
from automation.views.instruments import Instruments
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
FRAMES_AFTER_THE_LANDING: Final[int] = 3
BURST_READINGS: Final[str] = "frame_gaps.json"
HELD_BURST_READINGS: Final[str] = "frame_gaps_held.json"
LANDING_READINGS: Final[str] = "frame_gaps_landing.json"


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


def _keep_readings(name: str, readings: Dict[str, float]) -> None:
    """Prints the readings and keeps them beside the scenario's other files."""
    print(json.dumps(readings))
    (Path(os.environ[ARTIFACTS_VARIABLE]) / name).write_text(json.dumps(readings, indent=2))


def _zoom_in_on(screen: Screen, instruments: Instruments, graph: BarGraph) -> None:
    """Opens the long document's first pulse volume graph wide enough to drag its first bars."""
    expect_open(screen, LONG_RECONSTRUCTION)
    instruments.bring_forward(ChannelName.PULSE1)
    screen.hand.scroll_into_view(graph.plot)
    graph.zoom_in(NEAR_THE_START, ZOOM_NOTCHES)


def _wait_for_the_line_to_empty(screen: Screen) -> None:
    """Waits until the waveform's fade ends, which is when the last edit on its way has landed."""
    busy = screen.words(WAVEFORM_REGENERATING)
    screen.bridge.expect(
        screen.status,
        busy.__ne__,
        description="the line empty",
        timeout=DRAIN_TIMEOUT_SECONDS,
    )


def _drag_the_bars(instruments: Instruments, graph: BarGraph, releases: List[float]) -> None:
    """Drags each of :data:`DRAGGED_ITEMS` once, quiet and loud in turn, noting the clock at each release."""
    standing = instruments.envelope_items(ChannelName.PULSE1, FeatureKey.VOLUME)
    for turn, item in enumerate(DRAGGED_ITEMS):
        graph.drag_item(item, start=standing[item], end=QUIET if turn % 2 == 0 else LOUD)
        releases.append(time.monotonic())


@pytest.fixture(name="world")
def world_fixture() -> World:
    """The home holds the two-minute reconstruction with its recording."""
    return long_document_world()


@pytest.fixture(name="startup")
def startup_fixture() -> Startup:
    """The two-minute reconstruction is open at start, with no project."""
    return Startup(reconstruction=LONG_RECONSTRUCTION, project=None)


class TestADragOnALongDocument:
    """How the frames keep coming while envelope bars of a two-minute document are dragged.

    The scenario records the clock after every frame through a burst of drags and until the
    waveform's fade ends, then keeps the longest gap between two frames, how many gaps ran over a
    tenth of a second, the frames drawn a second, and how long the line took to empty after the
    last release, beside the scenario's other files. It holds the application to nothing: the
    readings are what a change to the edit path is judged by, taken before and after the change.
    """

    def test_the_frames_through_a_burst_of_drags(self, screen: Screen) -> None:
        """The readings are kept; the application is only asked to keep drawing and to leave cleanly."""
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        stamps: List[float] = []
        releases: List[float] = []

        def open_and_zoom_in(screen: Screen) -> None:
            _zoom_in_on(screen, instruments, graph)

        def drag_until_the_line_empties(screen: Screen) -> None:
            with screen.record(time.monotonic) as recording:
                _drag_the_bars(instruments, graph, releases)
                _wait_for_the_line_to_empty(screen)

            stamps.extend(recording.values())

        def keep_the_readings(screen: Screen) -> None:
            _keep_readings(BURST_READINGS, _frame_readings(stamps, releases[-1]))

        screen.scenario(open_and_zoom_in, drag_until_the_line_empties, keep_the_readings, leave_letting_it_go).run()


class TestADragWhileTheRebuildIsHeld:
    """What the interface itself costs per move: the same burst of drags with every rebuild held, so no
    edit lands while the bars move.

    The instruments panel draws each change as the pointer moves, so what the frames cost here is
    the panel's own drawing of a long document's envelopes, apart from any landing.
    """

    def test_the_frames_through_a_held_burst(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The readings are kept, then the held rebuilds are released and the application leaves cleanly."""
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        stamps: List[float] = []
        releases: List[float] = []

        def open_and_zoom_in(screen: Screen) -> None:
            _zoom_in_on(screen, instruments, graph)

        def drag_while_held(screen: Screen) -> None:
            with screen.record(time.monotonic) as recording:
                _drag_the_bars(instruments, graph, releases)

            stamps.extend(recording.values())
            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")

        def keep_the_readings(screen: Screen) -> None:
            _keep_readings(HELD_BURST_READINGS, _frame_readings(stamps, releases[-1]))

        def release_and_wait(screen: Screen) -> None:
            regeneration_hold.release()
            _wait_for_the_line_to_empty(screen)

        screen.scenario(
            open_and_zoom_in,
            drag_while_held,
            keep_the_readings,
            release_and_wait,
            leave_letting_it_go,
        ).run()


class TestOneLandingOnALongDocument:
    """What one landing costs on screen: a bar is dragged while the rebuild is held, and the frames are
    recorded from the release until the waveform's fade ends.

    The drag's own drawing happens before the recording starts, so the longest gap read here is the
    frame the landing holds up, with what the tab draws from it.
    """

    def test_the_frames_through_one_landing(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The readings are kept; the application is only asked to land the edit and to leave cleanly."""
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        stamps: List[float] = []
        released: List[float] = []

        def drag_one_bar_while_held(screen: Screen) -> None:
            _zoom_in_on(screen, instruments, graph)
            standing = instruments.envelope_items(ChannelName.PULSE1, FeatureKey.VOLUME)
            graph.drag_item(DRAGGED_ITEMS[0], start=standing[DRAGGED_ITEMS[0]], end=QUIET)
            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")

        def release_and_record_the_landing(screen: Screen) -> None:
            with screen.record(time.monotonic) as recording:
                regeneration_hold.release()
                released.append(time.monotonic())
                _wait_for_the_line_to_empty(screen)
                screen.frames(FRAMES_AFTER_THE_LANDING)

            stamps.extend(recording.values())

        def keep_the_readings(screen: Screen) -> None:
            _keep_readings(LANDING_READINGS, _frame_readings(stamps, released[0]))

        screen.scenario(
            drag_one_bar_while_held,
            release_and_record_the_landing,
            keep_the_readings,
            leave_letting_it_go,
        ).run()
