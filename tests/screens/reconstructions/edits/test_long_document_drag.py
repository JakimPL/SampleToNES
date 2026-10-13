import time
from typing import Final, List, Tuple

import pytest

from automation.application.startup import Startup
from automation.holds.regeneration import RegenerationHold
from automation.screen import Screen
from automation.steps.reconstructions import (
    LOUDEST,
    drag_item_to,
    expect_open,
    leave_letting_it_go,
    reconstruction_shade,
    shade_reading,
    wait_for_the_fade_to_end,
)
from automation.views.bar_graph import BarGraph
from automation.views.instruments import Instruments
from automation.worlds.home import World
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.readings import frame_readings, keep_readings
from tests.suite.screens.worlds.recordings import LONG_RECONSTRUCTION, long_document_world

DRAGGED_ITEMS: Final[Tuple[int, ...]] = (2, 4, 6, 8)
QUIET: Final[float] = 2.0
LOUD: Final[float] = 13.0
VOLUME_BOUNDS: Final[Tuple[int, int]] = (0, LOUDEST)
NEAR_THE_START: Final[float] = 0.05
ZOOM_NOTCHES: Final[int] = 5
FRAMES_AFTER_THE_LANDING: Final[int] = 3
BURST_READINGS: Final[str] = "frame_gaps.json"
HELD_BURST_READINGS: Final[str] = "frame_gaps_held.json"
LANDING_READINGS: Final[str] = "frame_gaps_landing.json"


def _zoom_in_on(screen: Screen, instruments: Instruments, graph: BarGraph) -> str:
    """Opens the long document's first pulse volume graph wide enough to drag its first bars.

    Returns:
        str: The shade the reconstruction line wears at rest, which the fade swaps.
    """
    expect_open(screen, LONG_RECONSTRUCTION)
    instruments.bring_forward(ChannelName.PULSE1)
    screen.hand.scroll_into_view(graph.plot)
    graph.zoom_in(NEAR_THE_START, ZOOM_NOTCHES)
    return reconstruction_shade(screen)


def _drag_the_bars(instruments: Instruments, graph: BarGraph, releases: List[float]) -> List[int]:
    """Drags each of :data:`DRAGGED_ITEMS` once, quiet and loud in turn, noting the clock at each release.

    Returns:
        List[int]: The volume items expected once every drag has landed.
    """
    expected = instruments.envelope_items(ChannelName.PULSE1, FeatureKey.VOLUME)
    for turn, item in enumerate(DRAGGED_ITEMS):
        _, expected = drag_item_to(graph, expected, item, end=QUIET if turn % 2 == 0 else LOUD, bounds=VOLUME_BOUNDS)
        releases.append(time.monotonic())

    return expected


def _expect_the_drags_drawn(screen: Screen, instruments: Instruments, expected: List[int]) -> None:
    """Waits until the volume items read as the drags left them."""
    screen.expect(
        lambda: instruments.envelope_items(ChannelName.PULSE1, FeatureKey.VOLUME),
        expected.__eq__,
        description="the drags drawn",
    )


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
    last release, beside the scenario's other files. The readings are what a change to the edit
    path is judged by, taken before and after the change. What the scenario holds the application
    to are the events: the fade is seen on some frame through the burst, ends once the rebuilds
    land, and the bars read as the drags left them.
    """

    def test_the_frames_through_a_burst_of_drags(self, screen: Screen) -> None:
        """The readings are kept; the fade begins and ends, the drags land, and the application leaves cleanly."""
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        stamps: List[float] = []
        releases: List[float] = []
        unfaded: List[str] = []
        expected: List[int] = []

        def open_and_zoom_in(screen: Screen) -> None:
            unfaded.append(_zoom_in_on(screen, instruments, graph))

        def drag_until_the_fade_ends(screen: Screen) -> None:
            shade = shade_reading(screen)
            with screen.record(lambda: (time.monotonic(), shade())) as recording:
                expected.extend(_drag_the_bars(instruments, graph, releases))
                wait_for_the_fade_to_end(screen, unfaded[0])

            readings = recording.values()
            stamps.extend(stamp for stamp, _ in readings)
            assert any(seen != unfaded[0] for _, seen in readings), "the fade was never seen through the burst"
            _expect_the_drags_drawn(screen, instruments, expected)

        def keep_the_readings(screen: Screen) -> None:
            keep_readings(BURST_READINGS, frame_readings(stamps, releases[-1]))

        screen.scenario(open_and_zoom_in, drag_until_the_fade_ends, keep_the_readings, leave_letting_it_go).run()


class TestADragWhileTheRebuildIsHeld:
    """What the interface itself costs per move: the same burst of drags with every rebuild held, so no
    edit lands while the bars move.

    The instruments panel draws each change as the pointer moves, so what the frames cost here is
    the panel's own drawing of a long document's envelopes, apart from any landing. The bars read as
    the drags left them before the rebuilds land and after.
    """

    def test_the_frames_through_a_held_burst(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The readings are kept, then the held rebuilds are released and the application leaves cleanly."""
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        stamps: List[float] = []
        releases: List[float] = []
        unfaded: List[str] = []
        expected: List[int] = []

        def open_and_zoom_in(screen: Screen) -> None:
            unfaded.append(_zoom_in_on(screen, instruments, graph))

        def drag_while_held(screen: Screen) -> None:
            with screen.record(time.monotonic) as recording:
                expected.extend(_drag_the_bars(instruments, graph, releases))

            stamps.extend(recording.values())
            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")
            assert reconstruction_shade(screen) != unfaded[0]
            _expect_the_drags_drawn(screen, instruments, expected)

        def keep_the_readings(screen: Screen) -> None:
            keep_readings(HELD_BURST_READINGS, frame_readings(stamps, releases[-1]))

        def release_and_wait(screen: Screen) -> None:
            regeneration_hold.release()
            wait_for_the_fade_to_end(screen, unfaded[0])
            _expect_the_drags_drawn(screen, instruments, expected)

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
    frame the landing holds up, with what the tab draws from it. The bar reads as the drag left it
    once the edit has landed.
    """

    def test_the_frames_through_one_landing(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The readings are kept; the edit lands, the fade ends, and the application leaves cleanly."""
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        stamps: List[float] = []
        released: List[float] = []
        unfaded: List[str] = []
        expected: List[int] = []

        def drag_one_bar_while_held(screen: Screen) -> None:
            unfaded.append(_zoom_in_on(screen, instruments, graph))
            standing = instruments.envelope_items(ChannelName.PULSE1, FeatureKey.VOLUME)
            _, items = drag_item_to(graph, standing, DRAGGED_ITEMS[0], end=QUIET, bounds=VOLUME_BOUNDS)
            expected.extend(items)
            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")
            assert reconstruction_shade(screen) != unfaded[0]

        def release_and_record_the_landing(screen: Screen) -> None:
            with screen.record(time.monotonic) as recording:
                regeneration_hold.release()
                released.append(time.monotonic())
                wait_for_the_fade_to_end(screen, unfaded[0])
                screen.frames(FRAMES_AFTER_THE_LANDING)

            stamps.extend(recording.values())
            _expect_the_drags_drawn(screen, instruments, expected)

        def keep_the_readings(screen: Screen) -> None:
            keep_readings(LANDING_READINGS, frame_readings(stamps, released[0]))

        screen.scenario(
            drag_one_bar_while_held,
            release_and_record_the_landing,
            keep_the_readings,
            leave_letting_it_go,
        ).run()
