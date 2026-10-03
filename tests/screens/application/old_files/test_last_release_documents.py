from typing import Tuple

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.playback import PlaybackConfig
from sampletones_core.compatibility.kind import ObjectKind
from tests.screens.application.old_files.constants import ARCHIVED_PROJECT, ARCHIVED_RECONSTRUCTION, BY_CONFIGURATION
from tests.screens.application.old_files.steps import stored_voice_names, world_of
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.archives import archived_document
from tests.suite.screens.seeds.recordings import stored_recording
from tests.suite.screens.worlds.home import World, screen_filling_state


class TestTheLastReleasesReconstruction:
    """A reconstruction the last release wrote opens in this build, its recording found where it names it."""

    @pytest.fixture
    def world(self) -> World:
        """The home holds the last release's reconstruction and its recording."""
        return world_of(
            archived_document(ObjectKind.RECONSTRUCTION, ARCHIVED_RECONSTRUCTION),
            stored_recording(),
        )

    def test_it_opens_from_the_browser(self, screen: Screen) -> None:
        """A double click on the browser's row opens the reconstruction with no notice shown.

        The scenario opens the by-configuration listing on the Reconstructions tab and double-clicks the
        row.
        """
        reconstructions = screen.reconstructions
        screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
        heading = screen.expect_item(
            lambda: reconstructions.browser.heading(screen.words(BY_CONFIGURATION)),
            description="the heading listing reconstructions by configuration",
        )
        reconstructions.browser.open_by_click(heading)
        row = screen.expect_item(
            lambda: reconstructions.browser.file_row(ARCHIVED_RECONSTRUCTION), description="its row"
        )

        reconstructions.browser.double_click(row)

        screen.expect(
            lambda: reconstructions.shows_open(ARCHIVED_RECONSTRUCTION),
            bool,
            description="the archived reconstruction open",
        )
        assert not screen.file_not_found_notice.is_shown()
        assert not screen.error_notice.is_shown()


class TestTheLastReleasesProject:
    """A project the last release wrote opens in this build, lists its voices and plays its song.

    The project opens at start with song looping on. The Sequencer lists the stored voices, Play turns the
    entry to Pause and enables Stop, and Stop returns the entry to Play.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds the last release's project and a session with song looping on."""
        looping = ApplicationConfig(playback=PlaybackConfig(loop_song=True))
        return World(
            state=screen_filling_state(),
            application_config=looping,
            config=None,
            files=(archived_document(ObjectKind.PROJECT, ARCHIVED_PROJECT),),
        )

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the archived project at start."""
        return Startup(reconstruction=None, project=ARCHIVED_PROJECT)

    def test_it_opens_at_start_lists_its_voices_and_plays_its_song(self, screen: Screen) -> None:
        """The voices match the stored ones, and playback starts and stops."""
        sequencer = screen.sequencer
        playing_entry = screen.words(_menu_key(MenuElements.ITEM_PLAYBACK_PAUSE))
        stopped_entry = screen.words(_menu_key(MenuElements.ITEM_PLAYBACK_PLAY))

        def lists_its_voices(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)

            screen.expect(sequencer.voices.names, stored_voice_names().__eq__, description="the stored voices")

        def plays(screen: Screen) -> None:
            assert sequencer.playback.play_entry() == stopped_entry

            sequencer.playback.play()

            screen.expect(sequencer.playback.play_entry, playing_entry.__eq__, description="Play reading Pause")
            assert sequencer.playback.can_stop()

        def stops(screen: Screen) -> None:
            sequencer.playback.stop()

            screen.expect(sequencer.playback.play_entry, stopped_entry.__eq__, description="Pause reading Play")
            assert not sequencer.playback.can_stop()

        screen.scenario(lists_its_voices, plays, stops).run()


class TestOpeningTheLastReleasesProjectFromTheMenu:
    """File > Open project opens a project the last release wrote."""

    @pytest.fixture
    def world(self) -> World:
        """The home holds the last release's project."""
        return world_of(archived_document(ObjectKind.PROJECT, ARCHIVED_PROJECT))

    def test_it_lists_the_stored_voices(self, screen: Screen) -> None:
        """The Sequencer lists the voices the file stores."""
        screen.tabs.bring_to_front(Tab.SEQUENCER)
        screen.answer_next_dialog(DialogKind.OPEN, ARCHIVED_PROJECT)

        screen.project.open()

        screen.expect(screen.sequencer.voices.names, stored_voice_names().__eq__, description="the stored voices")


def _menu_key(element: MenuElements) -> Tuple[Page, Panel, TextType, MenuElements]:
    """The language key of a menu label."""
    return (Page.GLOBAL, Panel.MENU, TextType.LABEL, element)
