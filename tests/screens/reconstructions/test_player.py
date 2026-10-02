import operator
from pathlib import Path
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.application import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Recording
from tests.suite.screens.steps.reconstructions import expect_open, load_from_the_browser
from tests.suite.screens.views.waveform import Waveform
from tests.suite.screens.world import (
    PLAYABLE_RECONSTRUCTION,
    SECOND_PLAYABLE,
    TAKES,
    World,
    playing_world,
)

SAMPLE_RATE: Final[int] = 44100
PLAYING_WINDOW_SECONDS: Final[float] = 3.0
STILL_FRAMES: Final[int] = 20
ZOOM_NOTCHES: Final[int] = 3
WIDTH_TOLERANCE: Final[float] = 0.01
SPACE_BURST: Final[int] = 5
PAST_THE_EDGE: Final[float] = 1.4
BEAT_FRAMES: Final[int] = 15
BEAT_LENGTH: Final[int] = 3
SILENCE: Final[float] = 1e-6
SILENT_SHARE_TOLERANCE: Final[float] = 0.05
PLAY: Final[str] = "global.menu.label.item_playback_play"
PAUSE: Final[str] = "global.menu.label.item_playback_pause"
RESUME: Final[str] = "global.menu.label.item_playback_resume"
ORIGINAL_SWITCH: Final[str] = "reconstructions.reconstruction.label.original_audio_radio"
RECONSTRUCTION_SWITCH: Final[str] = "reconstructions.reconstruction.label.reconstruction_radio"
ORIGINAL_LINE: Final[str] = "global.graph.label.waveform_original"
RECONSTRUCTION_LINE: Final[str] = "global.graph.label.waveform_reconstruction"


def entry(screen: Screen) -> str:
    """What the Playback menu's first entry reads: Play while stopped, Pause while playing, Resume while paused."""
    return screen.sequencer.playback.play_entry()


def expect_entry(screen: Screen, key: str) -> None:
    screen.expect(lambda: entry(screen), screen.words(key).__eq__, description=f"the Playback menu reading {key}")


def cursor(waveform: Waveform) -> float:
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


def advancing(screen: Screen, waveform: Waveform, after: float) -> float:
    return screen.expect(
        lambda: waveform.cursor() or -1.0,
        lambda reading: reading > after,
        description=f"the cursor moving past sample {after:.0f}",
    )


def held_still(screen: Screen, waveform: Waveform) -> float:
    """The cursor's sample, read twice some frames apart and found the same."""
    standing = cursor(waveform)
    screen.frames(STILL_FRAMES)
    assert waveform.cursor() == standing
    return standing


def width(limits: Tuple[float, float]) -> float:
    low, high = limits
    return high - low


def silent_share(drawn: List[float]) -> float:
    return sum(1 for height in drawn if abs(height) < SILENCE) / len(drawn)


class TestPlayingFromTheBrowser:
    """A reconstruction opened from the browser plays on Space, its cursor moving along the waveform."""

    def test_space_plays_and_the_cursor_moves_on(self, screen: Screen) -> None:
        waveform = screen.reconstructions.waveform

        def open_it(screen: Screen) -> None:
            load_from_the_browser(screen, PLAYABLE_RECONSTRUCTION)

            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            assert waveform.cursor() is None
            assert entry(screen) == screen.words(PLAY)

        def space_plays_it(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.PLAY)

            expect_entry(screen, PAUSE)
            first = screen.expect(waveform.cursor, bool, description="the cursor")
            assert first is not None
            advancing(screen, waveform, first)

        screen.scenario(open_it, space_plays_it).run()


class TestTheWaveformGestures:
    """A click plays from a point, moves the cursor while paused and jumps while playing; Space pauses and resumes.

    A drag pans the view and a double-click fits it, and neither moves the cursor or changes what plays.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_clicks_and_space_steer_playback(self, screen: Screen) -> None:
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
    """A triple click and a drag that leaves the plot play nothing, and the next plain click plays."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_a_triple_click_and_a_drag_off_the_plot_play_nothing(self, screen: Screen) -> None:
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
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_an_odd_burst_ends_playing(self, screen: Screen) -> None:
        waveform = screen.reconstructions.waveform
        expect_open(screen, PLAYABLE_RECONSTRUCTION)

        for _ in range(SPACE_BURST):
            screen.press_shortcut(ShortcutId.PLAY)

        expect_entry(screen, PAUSE)
        advancing(screen, waveform, cursor(waveform))
        screen.press_shortcut(ShortcutId.STOP)
        expect_entry(screen, PLAY)


class TestTheSourceSwitch:
    """The switch above the waveform puts the source it names on top of the waveform, and back."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_the_source_chosen_is_drawn_on_top(self, screen: Screen) -> None:
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
    """A reconstruction whose recording is gone offers the reconstruction alone."""

    @pytest.fixture
    def world(self) -> World:
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
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_the_switch_stays_on_the_reconstruction(self, screen: Screen) -> None:
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

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a reconstruction whose recording is missing draws a flat original line",
    )
    def test_the_waveform_draws_the_reconstruction_alone(self, screen: Screen) -> None:
        waveform = screen.reconstructions.waveform
        notice = screen.file_not_found_notice
        expect_open(screen, PLAYABLE_RECONSTRUCTION)
        screen.expect(notice.is_shown, bool, description="the notice about the recording")
        notice.dismiss()
        screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")

        assert waveform.series() == (waveform.series_tag(screen.words(RECONSTRUCTION_LINE)),)


class TestAnotherReconstructionAfterClosing:
    """A reconstruction opened after another was closed draws its cursor as it plays."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_its_cursor_moves_on(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        waveform = reconstructions.waveform

        def play_and_close_the_first(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            screen.press_shortcut(ShortcutId.PLAY)
            expect_entry(screen, PAUSE)
            screen.press_shortcut(ShortcutId.STOP)
            expect_entry(screen, PLAY)

            reconstructions.close_from_menu()

            screen.expect(reconstructions.file_line, operator.not_, description="nothing open")

        def open_the_second_and_play(screen: Screen) -> None:
            load_from_the_browser(screen, SECOND_PLAYABLE)
            expect_open(screen, SECOND_PLAYABLE)

            screen.press_shortcut(ShortcutId.PLAY)

            expect_entry(screen, PAUSE)
            first = screen.expect(waveform.cursor, bool, description="the cursor")
            assert first is not None
            advancing(screen, waveform, first)
            screen.press_shortcut(ShortcutId.STOP)
            expect_entry(screen, PLAY)

        screen.scenario(play_and_close_the_first, open_the_second_and_play).run()


class TestChoosingChannels:
    """The waveform draws the channels ticked above it, and ticking one back draws what it drew before."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_the_beat_alone_falls_silent_between_its_strokes(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        waveform = reconstructions.waveform
        line = screen.words(RECONSTRUCTION_LINE)
        drawn: Dict[str, List[float]] = {}

        def every_channel_sounds_throughout(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

            drawn["all"] = waveform.drawn(line)

            assert silent_share(drawn["all"]) == 0.0

        def the_beat_alone(screen: Screen) -> None:
            for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
                reconstructions.tick_channel(channel)

            beat = screen.expect(
                lambda: waveform.drawn(line),
                drawn["all"].__ne__,
                description="the waveform redrawn",
            )
            assert abs(silent_share(beat) - (BEAT_FRAMES - BEAT_LENGTH) / BEAT_FRAMES) <= SILENT_SHARE_TOLERANCE

        def every_channel_back(screen: Screen) -> None:
            for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
                reconstructions.tick_channel(channel)

            screen.expect(lambda: waveform.drawn(line), drawn["all"].__eq__, description="the waveform as before")

        screen.scenario(every_channel_sounds_throughout, the_beat_alone, every_channel_back).run()
