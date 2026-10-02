import operator
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.converter import ConverterConfig
from sampletones_application.config.session.application.favorites import Favorites
from sampletones_application.config.session.state.current import Current
from sampletones_application.config.session.state.paths import LastPaths
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.constants.output import OutputKind
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_PANEL
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.items import Item
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Recording
from tests.suite.screens.world import HomeFile, World, screen_filling_state
from tests.suite.screens.written import written_application_config, written_config, written_state

RECORDINGS_FOLDER: Final[str] = "Recordings"
UNTOUCHED_FOLDER: Final[str] = "Untouched"
LIBRARIES_FOLDER: Final[str] = "Libraries"
RECORDING_NAME: Final[str] = "kick.wav"
RECORDING_SECONDS: Final[float] = 0.25
RECORDING_FREQUENCY: Final[float] = 220.0
CHOSEN_CHANNELS_AT_ONCE: Final[int] = 2
SEEDED_CHANNELS_AT_ONCE: Final[int] = 3


def home_folder(name: str) -> Path:
    """A folder of the home the application was started in."""
    return Path.cwd() / name


def recording_in(folder: str) -> HomeFile:
    return Recording(
        destination=home_folder(folder) / RECORDING_NAME,
        seconds=RECORDING_SECONDS,
        frequency=RECORDING_FREQUENCY,
    )


def leave(screen: Screen) -> None:
    """Leaves through Exit, which writes the session, and waits for the application to stop."""
    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()


def world_with(state: ApplicationState, *files: HomeFile) -> World:
    return World(
        state=state,
        application_config=None,
        config=None,
        files=files,
    )


def state_with_advanced(shown: bool) -> ApplicationState:
    return screen_filling_state().model_copy(update={"advanced_settings": shown})


class TestTheAdvancedCardAcrossARestart:
    """Whether Advanced settings stands is written as the application leaves, and read as it starts."""

    @pytest.fixture(params=[False, True], ids=["hidden", "shown"])
    def seeded(self, request: pytest.FixtureRequest) -> bool:
        shown: bool = request.param
        return shown

    @pytest.fixture
    def world(self, seeded: bool) -> World:
        return world_with(state_with_advanced(seeded))

    def test_a_home_holding_it_shows_it(self, screen: Screen, seeded: bool) -> None:
        screen.expect(screen.main.advanced.is_shown, seeded.__eq__, description="the card as the session says")

    def test_leaving_writes_the_toggled_state(self, screen: Screen, seeded: bool) -> None:
        screen.press_shortcut(ShortcutId.TOGGLE_ADVANCED_SETTINGS)
        screen.expect(screen.main.advanced.is_shown, seeded.__ne__, description="the card toggled")

        leave(screen)

        assert written_state().advanced_settings is not seeded


class TestACollapsedCardAcrossARestart:
    """A card folded into its bar is written as the application leaves, and stands folded at the next start."""

    @pytest.fixture(params=[False, True], ids=["open", "collapsed"])
    def seeded(self, request: pytest.FixtureRequest) -> bool:
        collapsed: bool = request.param
        return collapsed

    @pytest.fixture
    def world(self, seeded: bool) -> World:
        state = screen_filling_state().model_copy(update={"collapsed_cards": {TAG_MAIN_CONVERTER_PANEL: seeded}})
        return world_with(state)

    def test_a_home_holding_it_shows_it(self, screen: Screen, seeded: bool) -> None:
        card = screen.main.card(TAG_MAIN_CONVERTER_PANEL)

        screen.expect(card.is_collapsed, seeded.__eq__, description="the Converter card as the session says")

    def test_leaving_writes_the_toggled_state(self, screen: Screen, seeded: bool) -> None:
        card = screen.main.card(TAG_MAIN_CONVERTER_PANEL)
        screen.expect(card.is_collapsed, seeded.__eq__, description="the Converter card as the session says")

        card.toggle()

        screen.expect(card.is_collapsed, seeded.__ne__, description="the Converter card toggled")
        leave(screen)
        assert written_state().collapsed_cards.get(TAG_MAIN_CONVERTER_PANEL) is not seeded


def explorer_world(opened: List[Path]) -> World:
    state = screen_filling_state().model_copy(update={"expanded_directories": opened})
    return world_with(state, recording_in(RECORDINGS_FOLDER), recording_in(UNTOUCHED_FOLDER))


def expect_row(screen: Screen, folder: Path) -> Item:
    return screen.expect_item(
        lambda: screen.explorer.file_row(folder),
        description=f"the row of {folder.name}",
    )


class TestLeavingWritesAFolderOpenedInTheExplorer:
    """A folder opened in the explorer is written as the application leaves; a sibling left closed is not."""

    @pytest.fixture
    def world(self) -> World:
        return explorer_world([])

    def test_the_session_names_the_opened_folder_alone(self, screen: Screen) -> None:
        explorer = screen.explorer
        opened = home_folder(RECORDINGS_FOLDER)
        row = expect_row(screen, opened)
        assert not explorer.is_open(row)

        explorer.double_click(row)

        screen.expect(lambda: explorer.is_open(row), bool, description="the folder open")
        leave(screen)
        written = written_state().expanded_directories
        assert opened in written
        assert home_folder(UNTOUCHED_FOLDER) not in written


class TestAHomeHoldingAnOpenedFolderShowsIt:
    """A folder the session names as opened stands open at the start; a sibling it leaves out stands closed."""

    @pytest.fixture
    def world(self) -> World:
        return explorer_world([home_folder(RECORDINGS_FOLDER)])

    def test_the_named_folder_stands_open_alone(self, screen: Screen) -> None:
        explorer = screen.explorer
        opened = expect_row(screen, home_folder(RECORDINGS_FOLDER))
        closed = expect_row(screen, home_folder(UNTOUCHED_FOLDER))

        screen.expect(lambda: explorer.is_open(opened), bool, description="the named folder open")
        assert not explorer.is_open(closed)


class TestTheTabInFrontAcrossARestart:
    """The tab in front is written as the application leaves, and brought forward at the next start."""

    @pytest.fixture
    def world(self) -> World:
        state = screen_filling_state().model_copy(update={"current": Current(tab=Tab.INSTRUCTIONS)})
        return world_with(state)

    def test_a_home_holding_it_shows_it_and_leaving_writes_the_next(self, screen: Screen) -> None:
        screen.expect(screen.tabs.front, Tab.INSTRUCTIONS.__eq__, description="the Instructions tab in front")

        screen.tabs.bring_to_front(Tab.SEQUENCER)

        screen.expect(screen.tabs.front, Tab.SEQUENCER.__eq__, description="the Sequencer tab in front")
        leave(screen)
        assert written_state().current.tab is Tab.SEQUENCER


def converter_config(output: OutputKind, channels_at_once: int) -> ConverterConfig:
    settings = StemSettings.covering(list(DEFAULT_CHANNELS)).model_copy(update={"channel_cap": channels_at_once})
    return ConverterConfig(output=output, settings=settings)


class TestTheConverterSettingsAcrossARestart:
    """The converter's output and its channels at once are written as the application leaves, and stand at the next start."""

    @pytest.fixture
    def world(self) -> World:
        return World(
            state=screen_filling_state(),
            application_config=ApplicationConfig(
                converter=converter_config(OutputKind.MIXED, SEEDED_CHANNELS_AT_ONCE),
            ),
            config=None,
            files=(),
        )

    def test_a_home_holding_them_shows_them_and_leaving_writes_the_next(self, screen: Screen) -> None:
        main = screen.main

        def shows_the_seeded_ones(screen: Screen) -> None:
            screen.expect(main.output, OutputKind.MIXED.__eq__, description="the output the settings name")
            assert main.lit_channels_at_once() == SEEDED_CHANNELS_AT_ONCE

        def changes_them(screen: Screen) -> None:
            main.choose_output(OutputKind.PER_RECORDING)
            main.choose_channels_at_once(CHOSEN_CHANNELS_AT_ONCE)

            screen.expect(main.lit_channels_at_once, CHOSEN_CHANNELS_AT_ONCE.__eq__, description="the step lit")
            assert main.output() is OutputKind.PER_RECORDING

        def leaving_writes_them(screen: Screen) -> None:
            leave(screen)

            converter = written_application_config().converter
            assert converter.output is OutputKind.PER_RECORDING
            assert converter.settings.channel_cap == CHOSEN_CHANNELS_AT_ONCE

        screen.scenario(shows_the_seeded_ones, changes_them, leaving_writes_them).run()


class TestTheLibraryFolderAcrossARestart:
    """The library folder Advanced settings points at is written as the application leaves, and named at the next start."""

    @pytest.fixture
    def world(self) -> World:
        config = Config()
        general = config.general.model_copy(update={"library_directory": str(home_folder(LIBRARIES_FOLDER))})
        return World(
            state=state_with_advanced(True),
            application_config=None,
            config=config.model_copy(update={"general": general}),
            files=(recording_in(LIBRARIES_FOLDER), recording_in(RECORDINGS_FOLDER)),
        )

    def test_a_home_holding_it_names_it_and_leaving_writes_the_next(self, screen: Screen) -> None:
        main = screen.main
        chosen = home_folder(RECORDINGS_FOLDER)

        def names_the_seeded_one(screen: Screen) -> None:
            screen.expect(
                main.library_directory,
                str(home_folder(LIBRARIES_FOLDER)).__eq__,
                description="the library folder the settings name",
            )

        def points_at_another(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.DIRECTORY, chosen)

            main.choose_library_directory()

            screen.expect(main.library_directory, str(chosen).__eq__, description="the chosen folder named")

        def leaving_writes_it(screen: Screen) -> None:
            leave(screen)

            assert Path(written_config().general.library_directory) == chosen

        screen.scenario(names_the_seeded_one, points_at_another, leaving_writes_it).run()


class TestADiscardedDisplayChange:
    """A Display settings change thrown away is never written, while one confirmed is."""

    def test_leaving_writes_only_the_confirmed_change(self, screen: Screen) -> None:
        settings = screen.display_settings
        prompt = settings.discard_prompt
        original: List[bool] = []

        def discard_a_change(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="the Display settings dialog")
            original.append(settings.vsync())
            settings.toggle_vsync()
            screen.expect(settings.vsync, original[0].__ne__, description="the box flipped")

            settings.cancel()
            screen.expect(prompt.is_shown, bool, description="the discard prompt")
            prompt.confirm()

            screen.expect(settings.is_shown, operator.not_, description="the dialog closed")

        def confirm_a_change(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="the dialog open again")
            assert settings.vsync() == original[0]
            settings.toggle_vsync()
            screen.expect(settings.vsync, original[0].__ne__, description="the box flipped")

            settings.confirm()

            screen.expect(settings.is_shown, operator.not_, description="the dialog closed")

        def leaving_writes_the_confirmed_one(screen: Screen) -> None:
            leave(screen)

            assert written_application_config().display.vsync is not original[0]

        screen.scenario(discard_a_change, confirm_a_change, leaving_writes_the_confirmed_one).run()


DELETED_FOLDER: Final[str] = "Deleted"
DELETED_SUBFOLDER: Final[str] = "Deeper"
DELETED_RECONSTRUCTION: Final[str] = "Deleted.stn"
DELETED_FAVORITE: Final[str] = "deleted.wav"


def deleted_folder() -> Path:
    return home_folder(DELETED_FOLDER) / DELETED_SUBFOLDER


def deleted_reconstruction() -> Path:
    return RECONSTRUCTIONS_DIRECTORY / DELETED_RECONSTRUCTION


def deleted_favorite() -> Path:
    return home_folder(DELETED_FAVORITE)


class TestASessionNamingDeletedFiles:
    """A session naming a folder, a reconstruction and a starred file deleted since the last run.

    The application starts with nothing restored and without a word, a dialog opens in the nearest
    folder still standing, and leaving writes none of the three back.
    """

    @pytest.fixture
    def world(self) -> World:
        state = screen_filling_state().model_copy(
            update={
                "current": Current(reconstruction=deleted_reconstruction()),
                "last_paths": LastPaths(reconstruction=deleted_folder()),
            }
        )
        return World(
            state=state,
            application_config=ApplicationConfig(favorites=Favorites(paths={deleted_favorite()})),
            config=None,
            files=(),
        )

    def test_it_restores_nothing_and_asks_in_the_nearest_standing_folder(self, screen: Screen) -> None:
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")
        screen.answer_next_dialog(DialogKind.OPEN, None)

        screen.reconstructions.open_from_menu()

        request = screen.expect(
            screen.dialog_requests,
            lambda requests: len(requests) == 1,
            description="the open dialog",
        )[0]
        assert request.initial_directory == Path.cwd()
        assert screen.shown_windows() == ()
        assert screen.reconstructions.open_file() == ""

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: leaving keeps the last dialog folder a run found deleted",
    )
    def test_the_session_left_names_neither_the_folder_nor_the_reconstruction(self, screen: Screen) -> None:
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")

        leave(screen)

        state = written_state()
        assert state.current.reconstruction is None
        assert state.last_paths.reconstruction != deleted_folder()

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: leaving keeps a starred file a run found deleted",
    )
    def test_the_settings_left_name_no_deleted_starred_file(self, screen: Screen) -> None:
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")

        leave(screen)

        assert deleted_favorite() not in written_application_config().favorites.paths
