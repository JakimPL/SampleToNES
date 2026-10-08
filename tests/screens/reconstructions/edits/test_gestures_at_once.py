import operator
from pathlib import Path
from typing import Final, List, Tuple

import pytest

from automation.application.startup import Startup
from automation.dearpygui.geometry import Point
from automation.holds.regeneration import RegenerationHold
from automation.screen import Screen
from automation.steps.project import save_project_as
from automation.steps.reconstructions import (
    expect_open,
    load_from_the_browser,
    marked,
    raise_the_first_level,
    raise_the_first_level_while_held,
    stored_levels,
    titled,
    voice_title,
)
from automation.steps.sequencer import open_voice
from automation.views.bar_graph import BarGraph
from automation.views.instruments import Instruments
from automation.vocabulary.dialogs import LOAD_TITLE
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.suite.screens.worlds.recordings import (
    OPEN_RECONSTRUCTION,
    PLAYABLE_RECONSTRUCTION,
    SECOND_PLAYABLE,
    SHORT_RECONSTRUCTION,
    SONG,
    SONG_SAMPLE,
    STEMS_RECONSTRUCTION,
)

DRAGGED_ITEM: Final[int] = 5
FIRST_ITEM: Final[int] = 1
QUIET: Final[float] = 4.0
LOUDEST: Final[int] = 15
ARPEGGIO_STEP: Final[float] = 12.0
ARPEGGIO_FLOOR: Final[int] = -128
ARPEGGIO_CEILING: Final[int] = 127
SAMPLE_ORDINAL: Final[int] = 0
LAST_RECORDING: Final[str] = "2"
SETTLE_FRAMES: Final[int] = 20
NEAR_THE_START: Final[float] = 0.05
ZOOM_NOTCHES: Final[int] = 5
SAVED_SONG: Final[Path] = PROJECTS_DIRECTORY / "Saved.stp"


def items(instruments: Instruments, channel: ChannelName, feature: FeatureKey) -> List[int]:
    """The items of the envelope that ``channel`` draws for ``feature``, read from the instruments panel."""
    return [int(item) for item in instruments.envelope(channel, feature).split()]


def dragged(
    graph: BarGraph,
    standing: List[int],
    *,
    end: float,
    bounds: Tuple[int, int],
) -> Tuple[int, List[int]]:
    """Drags the bar of the item :data:`DRAGGED_ITEM` to ``end`` and returns the item it moved and the items
    expected after.

    The item the plot puts under the release takes the value there, brought within ``bounds``, and every other
    item stands as it did.
    """
    release: Point = graph.drag_item(DRAGGED_ITEM, start=standing[DRAGGED_ITEM], end=end)
    index, value = graph.item_under(release)
    low, high = bounds
    expected = [*standing]
    expected[index] = min(max(round(value), low), high)
    return index, expected


def expect_items(
    screen: Screen, instruments: Instruments, channel: ChannelName, feature: FeatureKey, expected: List[int]
) -> None:
    """Waits until the envelope of ``channel`` and ``feature`` reads ``expected``."""
    screen.expect(
        lambda: items(instruments, channel, feature),
        expected.__eq__,
        description=f"{channel} {feature} as the edits left it",
    )


def leave_letting_it_go(screen: Screen) -> None:
    """Presses Exit, confirms the question about unsaved changes and waits for the application to close."""
    prompt = screen.reconstructions.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about leaving")

    prompt.confirm()

    assert screen.wait_for_exit()


class TestADragAndARemovalAtOnce:
    """A volume dragged and a recording removed while the drag is on its way both land.

    The rebuild is held while a volume item is dragged; a recording is removed and the removal confirmed
    meanwhile. After the rebuild is released, the recording is gone and the dragged value stands.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction with several recordings is open at start, with no project."""
        return Startup(reconstruction=STEMS_RECONSTRUCTION, project=None)

    def test_both_land(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The removed recording leaves the card and the dragged volume item keeps its new value."""
        reconstructions = screen.reconstructions
        instruments = reconstructions.instruments
        stems = reconstructions.stems
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        moved: List[Tuple[int, List[int]]] = []

        def drag_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, STEMS_RECONSTRUCTION)
            instruments.bring_forward(ChannelName.PULSE1)
            screen.hand.scroll_into_view(graph.plot)
            graph.zoom_in(NEAR_THE_START, ZOOM_NOTCHES)
            standing = items(instruments, ChannelName.PULSE1, FeatureKey.VOLUME)

            moved.append(dragged(graph, standing, end=QUIET, bounds=(0, LOUDEST)))

            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")

        def remove_a_recording_meanwhile(screen: Screen) -> None:
            stems.remove(LAST_RECORDING)
            screen.expect(stems.remove_prompt.is_shown, bool, description="the question about removing")

            stems.remove_prompt.confirm()

            screen.expect(stems.remove_prompt.is_shown, operator.not_, description="the question answered")
            assert stems.has_row(LAST_RECORDING)

        def both_land(screen: Screen) -> None:
            regeneration_hold.release()

            screen.expect(lambda: stems.has_row(LAST_RECORDING), operator.not_, description="the recording gone")
            index, expected = moved[0]
            screen.expect(
                lambda: items(instruments, ChannelName.PULSE1, FeatureKey.VOLUME)[: index + 1],
                expected[: index + 1].__eq__,
                description="the drag landed",
            )

        screen.scenario(
            drag_while_the_rebuild_is_held, remove_a_recording_meanwhile, both_land, leave_letting_it_go
        ).run()


class TestADragAndAnUndoAtOnce:
    """Undo pressed while a drag of a sample is on its way undoes the drag, and the edit saved before it stays.

    Consecutive edits of one sample run together into one entry of the history, and a save closes the run, so
    the edit before the drag stands in an entry of its own.

    A sample opens from the song, its first level is raised and the project is saved. With the rebuild held,
    an item is dragged and Undo pressed. Once released, the envelope reads as saved and holds there.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A project is open at start, with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_the_drag_is_undone(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The envelope returns to the values of the saved edit and stays there."""
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        edited: List[List[int]] = []

        def edit_the_sample_and_save(screen: Screen) -> None:
            open_voice(screen, SONG_SAMPLE)
            screen.expect(
                screen.title,
                voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=False).__eq__,
                description="the sample open",
            )
            regeneration_hold.release()
            raise_the_first_level(
                screen,
                ChannelName.PULSE1,
                title=voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=True),
            )
            edited.append(items(instruments, ChannelName.PULSE1, FeatureKey.VOLUME))

            save_project_as(screen, SAVED_SONG)

        def drag_and_undo_while_the_rebuild_is_held(screen: Screen) -> None:
            regeneration_hold.hold_again()
            screen.hand.scroll_into_view(graph.plot)
            release = graph.drag_item(FIRST_ITEM, start=edited[0][FIRST_ITEM], end=QUIET)
            index, _ = graph.item_under(release)
            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")
            assert items(instruments, ChannelName.PULSE1, FeatureKey.VOLUME)[index] != edited[0][index]

            screen.press_shortcut(ShortcutId.UNDO)

        def the_drag_alone_is_undone(screen: Screen) -> None:
            regeneration_hold.release()

            expect_items(screen, instruments, ChannelName.PULSE1, FeatureKey.VOLUME, edited[0])
            screen.frames(SETTLE_FRAMES)
            assert items(instruments, ChannelName.PULSE1, FeatureKey.VOLUME) == edited[0]

        screen.scenario(
            edit_the_sample_and_save, drag_and_undo_while_the_rebuild_is_held, the_drag_alone_is_undone
        ).run()


class TestADragAndASaveAtOnce:
    """A save asked for while a drag is on its way writes the drag.

    With the rebuild held, an item is dragged and Save pressed; the file stays as it was until the rebuild is
    released, then holds the dragged levels and the title shows a saved file.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A short reconstruction is open at start, with no project."""
        return Startup(reconstruction=SHORT_RECONSTRUCTION, project=None)

    def test_the_file_has_the_drag(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The saved file holds the dragged levels."""
        reconstructions = screen.reconstructions
        instruments = reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        moved: List[Tuple[int, List[int]]] = []
        stored: List[bytes] = []

        def drag_and_save_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, SHORT_RECONSTRUCTION)
            stored.append(SHORT_RECONSTRUCTION.read_bytes())
            instruments.bring_forward(ChannelName.PULSE1)
            screen.hand.scroll_into_view(graph.plot)
            standing = items(instruments, ChannelName.PULSE1, FeatureKey.VOLUME)
            moved.append(dragged(graph, standing, end=QUIET, bounds=(0, LOUDEST)))
            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")

            screen.press_shortcut(ShortcutId.SAVE_RECONSTRUCTION)

            screen.frames(SETTLE_FRAMES)
            assert SHORT_RECONSTRUCTION.read_bytes() == stored[0]

        def the_save_writes_the_drag(screen: Screen) -> None:
            regeneration_hold.release()

            index, expected = moved[0]
            screen.expect(
                lambda: stored_levels(SHORT_RECONSTRUCTION, ChannelName.PULSE1)[: index + 1],
                expected[: index + 1].__eq__,
                description="the file holding the drag",
            )
            screen.frames(SETTLE_FRAMES)
            assert screen.title() == titled(screen, SHORT_RECONSTRUCTION.name)

        screen.scenario(drag_and_save_while_the_rebuild_is_held, the_save_writes_the_drag).run()


class TestTwoDimensionsBeforeTheFadeEnds:
    """A volume and an arpeggio dragged one after the other while the first is on its way both stay.

    With the rebuild held, a volume item is dragged and then an arpeggio item. Once released, both envelopes
    hold their dragged values and the title shows unsaved changes.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A short reconstruction is open at start, with no project."""
        return Startup(reconstruction=SHORT_RECONSTRUCTION, project=None)

    def test_both_edits_stay(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The volume and the arpeggio envelopes both read their dragged values."""
        instruments = screen.reconstructions.instruments
        volume = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)
        arpeggio = instruments.graph(ChannelName.PULSE1, FeatureKey.ARPEGGIO)
        moved: List[Tuple[int, List[int]]] = []

        def drag_the_volume_while_held(screen: Screen) -> None:
            expect_open(screen, SHORT_RECONSTRUCTION)
            instruments.bring_forward(ChannelName.PULSE1)
            screen.hand.scroll_into_view(volume.plot)
            standing = items(instruments, ChannelName.PULSE1, FeatureKey.VOLUME)

            moved.append(dragged(volume, standing, end=QUIET, bounds=(0, LOUDEST)))

            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")

        def drag_the_arpeggio_meanwhile(screen: Screen) -> None:
            screen.hand.scroll_into_view(arpeggio.plot)
            standing = items(instruments, ChannelName.PULSE1, FeatureKey.ARPEGGIO)

            moved.append(dragged(arpeggio, standing, end=ARPEGGIO_STEP, bounds=(ARPEGGIO_FLOOR, ARPEGGIO_CEILING)))

        def both_stay(screen: Screen) -> None:
            regeneration_hold.release()

            expect_items(screen, instruments, ChannelName.PULSE1, FeatureKey.VOLUME, moved[0][1])
            expect_items(screen, instruments, ChannelName.PULSE1, FeatureKey.ARPEGGIO, moved[1][1])
            assert screen.title() == titled(screen, marked(SHORT_RECONSTRUCTION.name, unsaved=True))

        screen.scenario(
            drag_the_volume_while_held,
            drag_the_arpeggio_meanwhile,
            both_stay,
            leave_letting_it_go,
        ).run()


class TestTwoOpensWhileAnEditIsOnItsWay:
    """Two reconstructions double-clicked while an edit is on its way ask once, and the answer opens the second.

    The first level is raised while the rebuild is held, and two other reconstructions are double-clicked in
    the browser. Once released, one question about the unsaved changes shows. Discard opens the second
    reconstruction, and nothing asks after it.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_the_second_opens(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """One question shows, and Discard opens the reconstruction double-clicked last."""
        prompt = screen.reconstructions.unsaved_prompt

        def edit_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1)

        def open_two_while_it_is_held(screen: Screen) -> None:
            load_from_the_browser(screen, PLAYABLE_RECONSTRUCTION)
            load_from_the_browser(screen, SECOND_PLAYABLE)

            screen.frames(SETTLE_FRAMES)
            assert screen.shown_windows() == ()
            assert screen.reconstructions.shows_open(OPEN_RECONSTRUCTION)

        def the_edit_lands_and_one_question_comes(screen: Screen) -> None:
            regeneration_hold.release()

            screen.expect(prompt.is_shown, bool, description="the question about unsaved changes")
            assert prompt.title() == screen.words(LOAD_TITLE)
            screen.frames(SETTLE_FRAMES)
            assert len(screen.shown_windows()) == 1

        def discard_opens_the_second(screen: Screen) -> None:
            prompt.confirm()

            expect_open(screen, SECOND_PLAYABLE)
            screen.frames(SETTLE_FRAMES)
            assert screen.shown_windows() == ()
            assert screen.title() == titled(screen, SECOND_PLAYABLE.name)

        screen.scenario(
            edit_while_the_rebuild_is_held,
            open_two_while_it_is_held,
            the_edit_lands_and_one_question_comes,
            discard_opens_the_second,
        ).run()
