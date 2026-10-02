import operator
from functools import partial
from pathlib import Path
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_application.tags.general import TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.application import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open, load_from_the_browser, marked, titled
from tests.suite.screens.views.stems import StemsCard
from tests.suite.screens.world import (
    SHORT_RECONSTRUCTION,
    STEM_TAKES,
    STEMS_RECONSTRUCTION,
)

KEYS: Final[Tuple[str, ...]] = ("0", "1", "2")
FIRST: Final[str] = "0"
MIDDLE: Final[str] = "1"
LAST: Final[str] = "2"
STILL_FRAMES: Final[int] = 20
SILENT: Final[float] = 0.4
PLAYING_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE)
REMOVE_TITLE: Final[str] = "reconstructions.reconstruction.title.remove_stem_dialog"
REMOVE_MESSAGE: Final[str] = "reconstructions.reconstruction.message.remove_stem_message"
NOTHING_EXPORTED: Final[str] = "global.context.template.size_bytes"
PAUSE: Final[str] = "global.menu.label.item_playback_pause"


def take(index: int) -> Path:
    return Path.cwd() / STEM_TAKES[index]


def swatches(stems: StemsCard, keys: Tuple[str, ...]) -> Dict[str, Tuple[float, ...]]:
    return {key: stems.swatch(key) for key in keys}


def stems_title(screen: Screen, *, unsaved: bool) -> str:
    return titled(screen, marked(STEMS_RECONSTRUCTION.name, unsaved=unsaved))


class TestRevealingARecording:
    """A double-click on a row shows its recording in the file manager; a click shows nothing; no row stays lit."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=STEMS_RECONSTRUCTION, project=None)

    def test_a_double_click_shows_the_recording_and_leaves_the_row_plain(self, screen: Screen) -> None:
        stems = screen.reconstructions.stems

        def a_click_shows_nothing(screen: Screen) -> None:
            expect_open(screen, STEMS_RECONSTRUCTION)

            stems.click(FIRST)

            screen.frames(STILL_FRAMES)
            assert screen.revealed() == ()
            assert not any(stems.is_highlighted(key) for key in KEYS)

        def a_double_click_shows_that_recording(screen: Screen) -> None:
            stems.reveal(FIRST)

            screen.expect(screen.revealed, (take(0),).__eq__, description="the first recording shown")
            assert not any(stems.is_highlighted(key) for key in KEYS)

        def another_row_shows_its_own(screen: Screen) -> None:
            stems.reveal(LAST)

            screen.expect(screen.revealed, (take(0), take(2)).__eq__, description="the last recording shown")
            assert not any(stems.is_highlighted(key) for key in KEYS)

        screen.scenario(a_click_shows_nothing, a_double_click_shows_that_recording, another_row_shows_its_own).run()


class TestRemovingARecording:
    """Removing a recording asks first; the rest keep their colors and play, and the last one cannot go."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=STEMS_RECONSTRUCTION, project=None)

    def test_cancel_keeps_it_and_remove_leaves_the_rest_as_they_were(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        stems = reconstructions.stems
        prompt = stems.remove_prompt
        colors: List[Dict[str, Tuple[float, ...]]] = []

        def the_file_named(screen: Screen) -> None:
            expect_open(screen, STEMS_RECONSTRUCTION)

            assert screen.title() == stems_title(screen, unsaved=False)
            assert all(stems.has_row(key) for key in KEYS)
            colors.append(swatches(stems, KEYS))

        def cancel_keeps_it(screen: Screen) -> None:
            stems.remove(MIDDLE)
            screen.expect(prompt.is_shown, bool, description="the question about removing")
            assert prompt.title() == screen.words(REMOVE_TITLE)
            assert screen.words(REMOVE_MESSAGE) in prompt.words()

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
            screen.frames(STILL_FRAMES)
            assert all(stems.has_row(key) for key in KEYS)
            assert screen.title() == stems_title(screen, unsaved=False)

        def remove_the_middle(screen: Screen) -> None:
            stems.remove(MIDDLE)
            screen.expect(prompt.is_shown, bool, description="the question again")

            prompt.confirm()

            screen.expect(lambda: stems.has_row(MIDDLE), operator.not_, description="the middle recording gone")
            assert screen.title() == stems_title(screen, unsaved=True)
            assert swatches(stems, (FIRST, LAST)) == {key: colors[0][key] for key in (FIRST, LAST)}

        def the_rest_plays(screen: Screen) -> None:
            waveform = reconstructions.waveform

            screen.press_shortcut(ShortcutId.PLAY)

            screen.expect(screen.sequencer.playback.play_entry, screen.words(PAUSE).__eq__, description="playing")
            first = screen.expect(waveform.cursor, bool, description="the cursor")
            assert first is not None
            screen.expect(lambda: waveform.cursor() or 0.0, lambda reading: reading > first, description="moving on")
            screen.press_shortcut(ShortcutId.STOP)

        def the_last_cannot_go(screen: Screen) -> None:
            stems.remove(FIRST)
            screen.expect(prompt.is_shown, bool, description="the question about the first")
            prompt.confirm()
            screen.expect(lambda: stems.has_row(FIRST), operator.not_, description="the first recording gone")

            assert not stems.can_remove(LAST)
            assert stems.swatch(LAST) == colors[0][LAST]

        def saved_and_opened_again_it_keeps_its_color(screen: Screen) -> None:
            reconstructions.save_from_menu()
            screen.expect(screen.title, stems_title(screen, unsaved=False).__eq__, description="saved")
            reconstructions.close_from_menu()
            screen.expect(reconstructions.file_line, operator.not_, description="closed")

            load_from_the_browser(screen, STEMS_RECONSTRUCTION)

            expect_open(screen, STEMS_RECONSTRUCTION)
            screen.expect(lambda: stems.has_row(LAST), bool, description="the last recording listed")
            assert not stems.has_row(FIRST)
            assert not stems.has_row(MIDDLE)
            assert stems.swatch(LAST) == colors[0][LAST]

        screen.scenario(
            the_file_named,
            cancel_keeps_it,
            remove_the_middle,
            the_rest_plays,
            the_last_cannot_go,
            saved_and_opened_again_it_keeps_its_color,
        ).run()


class TestSilencingARecording:
    """A recording whose every frame falls silent leaves the card, and the others keep their colors.

    With the middle recording heard alone, each channel's volume is dragged to silence across every
    bar, which leaves the channel standing by for that recording.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=STEMS_RECONSTRUCTION, project=None)

    def test_its_row_leaves_and_the_others_keep_their_colors(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        stems = reconstructions.stems
        instruments = reconstructions.instruments
        colors: List[Dict[str, Tuple[float, ...]]] = []

        def hear_the_middle_alone(screen: Screen) -> None:
            expect_open(screen, STEMS_RECONSTRUCTION)
            colors.append(swatches(stems, KEYS))

            for key in (FIRST, LAST):
                stems.tick(key)
                screen.expect(partial(stems.hears, key), operator.not_, description=f"{key} left unheard")

        def silence_every_channel_of_it(screen: Screen) -> None:
            for channel in PLAYING_CHANNELS:
                instruments.bring_forward(channel)
                graph = instruments.graph(channel, FeatureKey.VOLUME)
                screen.hand.scroll_into_view(graph.plot)

                bars = len(instruments.envelope(channel, FeatureKey.VOLUME).split())

                graph.drag_across(0, bars - 1, value=SILENT)

                screen.expect(
                    partial(instruments.envelope, channel, FeatureKey.VOLUME),
                    operator.not_,
                    description=f"{channel} standing by",
                )

        def its_row_leaves(screen: Screen) -> None:
            screen.expect(lambda: stems.has_row(MIDDLE), operator.not_, description="the middle recording gone")

            assert swatches(stems, (FIRST, LAST)) == {key: colors[0][key] for key in (FIRST, LAST)}

        def leave_letting_it_go(screen: Screen) -> None:
            prompt = reconstructions.unsaved_prompt
            screen.press_shortcut(ShortcutId.EXIT)
            screen.expect(prompt.is_shown, bool, description="the question about leaving")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(hear_the_middle_alone, silence_every_channel_of_it, its_row_leaves, leave_letting_it_go).run()


class TestLettingAChannelGo:
    """A channel whose volume is dragged to silence on every frame mutes its tab and exports nothing.

    The silence is dragged at a height that rounds to it, above the strip under the bars that a
    press ignores.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=SHORT_RECONSTRUCTION, project=None)

    def test_the_tab_mutes_and_its_size_reads_nothing(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        instruments = reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)

        def drag_pulse_one_to_silence(screen: Screen) -> None:
            expect_open(screen, SHORT_RECONSTRUCTION)
            instruments.bring_forward(ChannelName.PULSE1)
            screen.hand.scroll_into_view(graph.plot)
            assert instruments.tab_theme(ChannelName.PULSE1) != TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED

            bars = len(instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME).split())

            graph.drag_across(0, bars - 1, value=SILENT)

            screen.expect(
                lambda: instruments.tab_theme(ChannelName.PULSE1),
                TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED.__eq__,
                description="the tab muted",
            )
            assert instruments.size(ChannelName.PULSE1) == screen.words(NOTHING_EXPORTED).format(bytes=0)
            assert not instruments.can_export(ChannelName.PULSE1)

        def leave_letting_it_go(screen: Screen) -> None:
            prompt = reconstructions.unsaved_prompt
            screen.press_shortcut(ShortcutId.EXIT)
            screen.expect(prompt.is_shown, bool, description="the question about leaving")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(drag_pulse_one_to_silence, leave_letting_it_go).run()
