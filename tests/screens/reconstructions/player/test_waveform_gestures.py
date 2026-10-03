import operator
from typing import Final, List, Tuple

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.reconstructions.player.steps import advancing, entry, expect_entry
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.views.waveform import Waveform
from tests.suite.screens.vocabulary.playback import PAUSE, PLAY
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION

SAMPLE_RATE: Final[int] = 44100
PLAYING_WINDOW_SECONDS: Final[float] = 3.0
STILL_FRAMES: Final[int] = 20
ZOOM_NOTCHES: Final[int] = 3
WIDTH_TOLERANCE: Final[float] = 0.01
SPACE_BURST: Final[int] = 5
PAST_THE_EDGE: Final[float] = 1.4
RESUME: Final[str] = "global.menu.label.item_playback_resume"


def cursor(waveform: Waveform) -> float:
    """The cursor's sample on the waveform, which must be drawn."""
    found = waveform.cursor()
    assert found is not None, "no cursor stands on the waveform"
    return found


def playing_from(screen: Screen, waveform: Waveform, sample: float) -> float:
    """Waits for the cursor to stand at ``sample`` or a little past it, where playing from ``sample`` puts it."""
    window = PLAYING_WINDOW_SECONDS * SAMPLE_RATE
    return screen.expect(
        lambda: waveform.cursor() or -1.0,
        lambda reading: sample <= reading < sample + window,
        description=f"the cursor playing on from sample {sample:.0f}",
    )


def held_still(screen: Screen, waveform: Waveform) -> float:
    """The cursor's sample, read twice some frames apart and found the same."""
    standing = cursor(waveform)
    screen.frames(STILL_FRAMES)
    assert waveform.cursor() == standing
    return standing


def width(limits: Tuple[float, float]) -> float:
    """The span a pair of axis limits covers."""
    low, high = limits
    return high - low


class TestTheWaveformGestures:
    """A click plays from a point, moves the cursor while paused and jumps while playing; Space pauses and
    resumes.

    A drag pans the view and a double-click fits it, and both leave the cursor and what plays as they were.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_clicks_and_space_steer_playback(self, screen: Screen) -> None:
        """A click plays from there, Space pauses and resumes, and Stop takes the cursor away."""
        waveform = screen.reconstructions.waveform
        stood: List[float] = []

        def a_click_while_stopped_plays_from_there(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            under = waveform.sample_under(0.5)

            waveform.click(0.5)

            expect_entry(screen, PAUSE)
            playing_from(screen, waveform, under)

        def space_pauses_and_the_cursor_holds(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.PLAY)

            expect_entry(screen, RESUME)
            screen.frames(STILL_FRAMES)
            held_still(screen, waveform)

        def a_click_while_paused_moves_the_cursor_and_stays_paused(screen: Screen) -> None:
            under = waveform.sample_under(0.25)

            waveform.click(0.25)

            screen.expect(waveform.cursor, float(round(under)).__eq__, description="the cursor where clicked")
            stood.append(held_still(screen, waveform))
            assert entry(screen) == screen.words(RESUME)

        def space_resumes_from_the_cursor(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.PLAY)

            expect_entry(screen, PAUSE)
            playing_from(screen, waveform, stood[0])

        def a_click_while_playing_jumps_there(screen: Screen) -> None:
            under = waveform.sample_under(0.75)

            waveform.click(0.75)

            playing_from(screen, waveform, under)
            assert entry(screen) == screen.words(PAUSE)

        def stop_takes_the_cursor_away(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.STOP)

            expect_entry(screen, PLAY)
            screen.expect(waveform.cursor, operator.not_, description="no cursor")

        screen.scenario(
            a_click_while_stopped_plays_from_there,
            space_pauses_and_the_cursor_holds,
            a_click_while_paused_moves_the_cursor_and_stays_paused,
            space_resumes_from_the_cursor,
            a_click_while_playing_jumps_there,
            stop_takes_the_cursor_away,
        ).run()

    def test_a_drag_pans_and_a_double_click_fits_without_touching_playback(self, screen: Screen) -> None:
        """A drag pans the zoomed view and a double-click fits it again, while the pause, the playing and the
        stop go on as they were.
        """
        waveform = screen.reconstructions.waveform
        fitted: List[Tuple[float, float]] = []
        stood: List[float] = []

        def pause_partway(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            fitted.append(
                screen.expect(waveform.limits, lambda limits: limits[1] > SAMPLE_RATE, description="the view fitted")
            )
            waveform.click(0.5)
            expect_entry(screen, PAUSE)

            screen.press_shortcut(ShortcutId.PLAY)

            expect_entry(screen, RESUME)
            screen.frames(STILL_FRAMES)
            stood.append(held_still(screen, waveform))

        def zoom_in_and_drag(screen: Screen) -> None:
            waveform.zoom_in(0.5, ZOOM_NOTCHES)
            zoomed = screen.expect(
                waveform.limits, lambda limits: width(limits) < width(fitted[0]), description="zoomed"
            )

            waveform.drag(0.6, 0.4)

            panned = screen.expect(waveform.limits, lambda limits: limits[0] > zoomed[0], description="panned")
            assert abs(width(panned) - width(zoomed)) <= WIDTH_TOLERANCE * width(zoomed)
            assert waveform.cursor() == stood[0]
            assert entry(screen) == screen.words(RESUME)

        def a_double_click_fits_and_leaves_the_pause(screen: Screen) -> None:
            waveform.double_click(0.5)

            screen.expect(waveform.limits, fitted[0].__eq__, description="the view fitted")
            screen.frames(STILL_FRAMES)
            assert waveform.cursor() == stood[0]
            assert entry(screen) == screen.words(RESUME)

        def a_double_click_leaves_playing_playing(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.PLAY)
            expect_entry(screen, PAUSE)
            waveform.zoom_in(0.5, ZOOM_NOTCHES)
            screen.expect(waveform.limits, lambda limits: width(limits) < width(fitted[0]), description="zoomed")
            before = cursor(waveform)

            waveform.double_click(0.5)

            screen.expect(waveform.limits, fitted[0].__eq__, description="the view fitted")
            assert entry(screen) == screen.words(PAUSE)
            advancing(screen, waveform, before)

        def a_double_click_leaves_stopped_stopped(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.STOP)
            expect_entry(screen, PLAY)
            waveform.zoom_in(0.5, ZOOM_NOTCHES)
            screen.expect(waveform.limits, lambda limits: width(limits) < width(fitted[0]), description="zoomed")

            waveform.double_click(0.5)

            screen.expect(waveform.limits, fitted[0].__eq__, description="the view fitted")
            screen.frames(STILL_FRAMES)
            assert waveform.cursor() is None
            assert entry(screen) == screen.words(PLAY)

        screen.scenario(
            pause_partway,
            zoom_in_and_drag,
            a_double_click_fits_and_leaves_the_pause,
            a_double_click_leaves_playing_playing,
            a_double_click_leaves_stopped_stopped,
        ).run()


class TestPressesThatAreNoClick:
    """A triple click and a drag that leaves the plot play nothing, and the next plain click plays.

    The scenario triple-clicks, then drags past the plot's edge on a zoomed view, and expects the cursor
    absent and the menu reading Play both times. A plain click then plays, and Stop ends it.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_a_triple_click_and_a_drag_off_the_plot_play_nothing(self, screen: Screen) -> None:
        """The triple click and the drag off the plot leave the cursor absent and the menu reading Play."""
        waveform = screen.reconstructions.waveform

        def a_triple_click(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)

            waveform.triple_click(0.5)

            screen.frames(STILL_FRAMES)
            assert waveform.cursor() is None
            assert entry(screen) == screen.words(PLAY)

        def a_drag_off_the_plot(screen: Screen) -> None:
            waveform.zoom_in(0.5, ZOOM_NOTCHES)

            waveform.drag(0.5, PAST_THE_EDGE)

            screen.frames(STILL_FRAMES)
            assert waveform.cursor() is None
            assert entry(screen) == screen.words(PLAY)

        def a_plain_click_plays(screen: Screen) -> None:
            under = waveform.sample_under(0.5)

            waveform.click(0.5)

            expect_entry(screen, PAUSE)
            playing_from(screen, waveform, under)
            screen.press_shortcut(ShortcutId.STOP)
            expect_entry(screen, PLAY)

        screen.scenario(a_triple_click, a_drag_off_the_plot, a_plain_click_plays).run()


class TestABurstOfSpace:
    """Five presses of Space from a stop play, pause, resume, pause and resume: the burst ends playing."""

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_an_odd_burst_ends_playing(self, screen: Screen) -> None:
        """After the burst the menu reads Pause and the cursor moves on."""
        waveform = screen.reconstructions.waveform
        expect_open(screen, PLAYABLE_RECONSTRUCTION)

        for _ in range(SPACE_BURST):
            screen.press_shortcut(ShortcutId.PLAY)

        expect_entry(screen, PAUSE)
        advancing(screen, waveform, cursor(waveform))
        screen.press_shortcut(ShortcutId.STOP)
        expect_entry(screen, PLAY)
