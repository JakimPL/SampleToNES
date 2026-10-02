import json
import operator
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Final, List, Optional, Tuple, Type

import pytest
import yaml

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.playback import PlaybackConfig
from sampletones_application.config.session.state.current import Current
from sampletones_application.paths import APPLICATION_STATE_PATH
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.configs import Config, InstructionsLibraryConfig
from sampletones_core.fft import Window
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_shared.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_PROJECT_DATA_VERSION,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)
from sampletones_shared.exceptions.reconstruction import (
    IncompatibleReconstructionVersionError,
    InvalidReconstructionValuesError,
)
from sampletones_shared.paths.user import CONFIG_PATH, LIBRARY_DIRECTORY, PROJECTS_DIRECTORY, RECONSTRUCTIONS_DIRECTORY
from tests.suite.compatibility import ARCHIVED_VERSIONS, archived, stored_document, stored_version
from tests.suite.screens.application import NOTHING_TO_OPEN, Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.items import Item
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Damage, Recording, WrittenBytes, archived_document, damaged_document
from tests.suite.screens.views.notices import Notice
from tests.suite.screens.world import HomeFile, World, screen_filling_state

ARCHIVED_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Archived.stn"
SECOND_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Second.stn"
ARCHIVED_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Archived.stp"
SECOND_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Second.stp"
VANISHED: Final[str] = "vanished"
OLDER_RECONSTRUCTION_VERSION: Final[str] = "2.0"
OLDER_PROJECT_VERSION: Final[str] = "0.9"
RECORDING_SECONDS: Final[float] = 0.5
RECORDING_FREQUENCY: Final[float] = 220.0
AUDIO_PATH_FIELD: Final[str] = "audio_filepath"
SAMPLES_FIELD: Final[str] = "samples"
NAME_FIELD: Final[str] = "name"
CONFIG_FIELD: Final[str] = "config"
INVALID_VALUES: Final[str] = "reconstructions.browser.message.invalid_values"
INCOMPATIBLE_VERSION: Final[str] = "reconstructions.browser.template.incompatible_version_template"
RECONSTRUCTION_NOT_FOUND: Final[str] = "reconstructions.browser.message.file_not_found"
BY_CONFIGURATION: Final[str] = "global.browser.label.by_configuration"


def future_version(current: str) -> str:
    """A data version past the one this build writes, which no build has written yet."""
    major, _ = current.split(".", 1)
    return f"{int(major) + 1}.0"


def stored_recording() -> Recording:
    """The recording the archived reconstruction names, laid where its relative path leads from the home.

    The application runs in the home, so a relative path the document names resolves there.
    """
    document = stored_document(archived(ObjectKind.RECONSTRUCTION, ARCHIVED_VERSIONS[ObjectKind.RECONSTRUCTION]))
    return Recording(
        destination=Path.cwd() / document[AUDIO_PATH_FIELD],
        seconds=RECORDING_SECONDS,
        frequency=RECORDING_FREQUENCY,
    )


def stored_voice_names() -> List[str]:
    """The voice names the archived project stores, read off its document without the application's model."""
    document = stored_document(archived(ObjectKind.PROJECT, ARCHIVED_VERSIONS[ObjectKind.PROJECT]))
    return [sample[NAME_FIELD] for sample in document[SAMPLES_FIELD]]


def damaged_name(damage: Damage, suffix: str) -> str:
    return f"{damage.name.lower()}{suffix}"


def damaged_reconstruction(damage: Damage) -> HomeFile:
    return damaged_document(
        ObjectKind.RECONSTRUCTION,
        damage,
        destination=RECONSTRUCTIONS_DIRECTORY / damaged_name(damage, ".stn"),
        older_version=OLDER_RECONSTRUCTION_VERSION,
        future_version=future_version(SAMPLETONES_RECONSTRUCTION_DATA_VERSION),
    )


def damaged_project(damage: Damage) -> HomeFile:
    return damaged_document(
        ObjectKind.PROJECT,
        damage,
        destination=PROJECTS_DIRECTORY / damaged_name(damage, ".stp"),
        older_version=OLDER_PROJECT_VERSION,
        future_version=future_version(SAMPLETONES_PROJECT_DATA_VERSION),
    )


def stated_version(damage: Damage, current: str, older: str) -> str:
    return older if damage is Damage.OLDER_VERSION else future_version(current)


def world_of(*files: HomeFile) -> World:
    return World(
        state=screen_filling_state(),
        application_config=None,
        config=None,
        files=files,
    )


def reconstruction_refusal(screen: Screen, damage: Damage) -> str:
    """What the application says refusing a reconstruction with ``damage``, as the language file words it."""
    match damage:
        case Damage.OLDER_VERSION | Damage.FUTURE_VERSION:
            stated = stated_version(damage, SAMPLETONES_RECONSTRUCTION_DATA_VERSION, OLDER_RECONSTRUCTION_VERSION)
            return screen.words(INCOMPATIBLE_VERSION).format(stated, SAMPLETONES_RECONSTRUCTION_DATA_VERSION)
        case Damage.TRUNCATED | Damage.FOREIGN_BYTES:
            return screen.words(INVALID_VALUES)


def reconstruction_failure(damage: Optional[Damage]) -> Type[BaseException]:
    """The failure the application records for a reconstruction with ``damage``, or for a file gone."""
    match damage:
        case Damage.OLDER_VERSION | Damage.FUTURE_VERSION:
            return IncompatibleReconstructionVersionError
        case Damage.TRUNCATED | Damage.FOREIGN_BYTES:
            return InvalidReconstructionValuesError
        case None:
            return FileNotFoundError


def shown_notice(screen: Screen) -> Notice:
    notices = (screen.error_notice, screen.file_not_found_notice)
    screen.expect(lambda: any(notice.is_shown() for notice in notices), bool, description="a notice")
    return next(notice for notice in notices if notice.is_shown())


class TestTheLastReleasesReconstruction:
    """A reconstruction the last release wrote opens in this build, its recording found where it names it."""

    @pytest.fixture
    def world(self) -> World:
        return world_of(
            archived_document(ObjectKind.RECONSTRUCTION, ARCHIVED_RECONSTRUCTION),
            stored_recording(),
        )

    def test_it_opens_from_the_browser(self, screen: Screen) -> None:
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
    """A project the last release wrote opens in this build, lists its voices and plays its song."""

    @pytest.fixture
    def world(self) -> World:
        looping = ApplicationConfig(playback=PlaybackConfig(loop_song=True))
        return World(
            state=screen_filling_state(),
            application_config=looping,
            config=None,
            files=(archived_document(ObjectKind.PROJECT, ARCHIVED_PROJECT),),
        )

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=ARCHIVED_PROJECT)

    def test_it_opens_at_start_lists_its_voices_and_plays_its_song(self, screen: Screen) -> None:
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
    """File ▸ Open project opens a project the last release wrote."""

    @pytest.fixture
    def world(self) -> World:
        return world_of(archived_document(ObjectKind.PROJECT, ARCHIVED_PROJECT))

    def test_it_lists_the_stored_voices(self, screen: Screen) -> None:
        screen.tabs.bring_to_front(Tab.SEQUENCER)
        screen.answer_next_dialog(DialogKind.OPEN, ARCHIVED_PROJECT)

        screen.project.open()

        screen.expect(screen.sequencer.voices.names, stored_voice_names().__eq__, description="the stored voices")


def _menu_key(element: MenuElements) -> Tuple[Page, Panel, TextType, MenuElements]:
    return (Page.GLOBAL, Panel.MENU, TextType.LABEL, element)


DOOR_SUFFIX_RECONSTRUCTION: Final[str] = ".stn"
DOOR_SUFFIX_PROJECT: Final[str] = ".stp"


def broken_reconstruction_world() -> World:
    return world_of(
        archived_document(ObjectKind.RECONSTRUCTION, ARCHIVED_RECONSTRUCTION),
        archived_document(ObjectKind.RECONSTRUCTION, SECOND_RECONSTRUCTION),
        archived_document(ObjectKind.RECONSTRUCTION, RECONSTRUCTIONS_DIRECTORY / f"{VANISHED}.stn"),
        stored_recording(),
        *(damaged_reconstruction(damage) for damage in Damage),
    )


def refused_reconstruction(
    screen: Screen,
    damage: Optional[Damage],
    expected: str,
) -> None:
    """Reads the notice refusing a reconstruction, dismisses it, and checks the reconstruction open before stands."""
    notice = shown_notice(screen)
    words = notice.words()
    screen.claim_error(reconstruction_failure(damage).__name__)

    notice.dismiss()

    screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")
    assert words.startswith(expected), words
    assert screen.reconstructions.shows_open(ARCHIVED_RECONSTRUCTION)


class TestRefusingABrokenReconstruction:
    """A reconstruction that cannot be read is refused with a readable message, and the one open stays open.

    Each door that opens a reconstruction is walked with every kind of damage, and then with a file
    removed after it was listed or chosen. The last gesture opens a sound reconstruction the same
    way, which shows the door still opens what it should.
    """

    @pytest.fixture
    def world(self) -> World:
        return broken_reconstruction_world()

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=ARCHIVED_RECONSTRUCTION, project=None)

    def test_through_the_browser(self, screen: Screen) -> None:
        browser = screen.reconstructions.browser
        vanished = RECONSTRUCTIONS_DIRECTORY / f"{VANISHED}.stn"

        def open_the_listing(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
            heading = screen.expect_item(
                lambda: browser.heading(screen.words(BY_CONFIGURATION)),
                description="the heading listing reconstructions by configuration",
            )
            browser.open_by_click(heading)

        def refuse_each_damage(screen: Screen) -> None:
            for damage in Damage:
                path = RECONSTRUCTIONS_DIRECTORY / damaged_name(damage, DOOR_SUFFIX_RECONSTRUCTION)
                row = screen.expect_item(partial(browser.file_row, path), description="its row")

                browser.double_click(row)

                refused_reconstruction(screen, damage, reconstruction_refusal(screen, damage))

        def refuse_a_file_removed_after_it_was_listed(screen: Screen) -> None:
            row = screen.expect_item(lambda: browser.file_row(vanished), description="its row")
            vanished.unlink()

            browser.double_click(row)

            refused_reconstruction(screen, None, screen.words(RECONSTRUCTION_NOT_FOUND))

        def open_a_sound_one_the_same_way(screen: Screen) -> None:
            row = screen.expect_item(lambda: browser.file_row(SECOND_RECONSTRUCTION), description="its row")

            browser.double_click(row)

            screen.expect(
                lambda: screen.reconstructions.shows_open(SECOND_RECONSTRUCTION),
                bool,
                description="the sound reconstruction open",
            )

        screen.scenario(
            open_the_listing,
            refuse_each_damage,
            refuse_a_file_removed_after_it_was_listed,
            open_a_sound_one_the_same_way,
        ).run()

    def test_through_reconstruction_open(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        vanished = RECONSTRUCTIONS_DIRECTORY / f"{VANISHED}.stn"

        def refuse_each_damage(screen: Screen) -> None:
            for damage in Damage:
                path = RECONSTRUCTIONS_DIRECTORY / damaged_name(damage, DOOR_SUFFIX_RECONSTRUCTION)
                screen.answer_next_dialog(DialogKind.OPEN, path)

                reconstructions.open_from_menu()

                refused_reconstruction(screen, damage, reconstruction_refusal(screen, damage))

        def refuse_a_file_removed_after_it_was_chosen(screen: Screen) -> None:
            vanished.unlink()
            screen.answer_next_dialog(DialogKind.OPEN, vanished)

            reconstructions.open_from_menu()

            refused_reconstruction(screen, None, screen.words(RECONSTRUCTION_NOT_FOUND))

        def open_a_sound_one_the_same_way(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, SECOND_RECONSTRUCTION)

            reconstructions.open_from_menu()

            screen.expect(
                lambda: reconstructions.shows_open(SECOND_RECONSTRUCTION),
                bool,
                description="the sound reconstruction open",
            )

        screen.scenario(
            refuse_each_damage,
            refuse_a_file_removed_after_it_was_chosen,
            open_a_sound_one_the_same_way,
        ).run()


@dataclass(frozen=True)
class StartupCase:
    """A broken document handed to the application as it starts: the damage, or its file gone."""

    damage: Optional[Damage]

    def name(self, suffix: str) -> str:
        return damaged_name(self.damage, suffix) if self.damage is not None else f"{VANISHED}{suffix}"


STARTUP_CASES: Final[Tuple[StartupCase, ...]] = (*(StartupCase(damage) for damage in Damage), StartupCase(None))


class TestABrokenReconstructionGivenAtStart:
    """A reconstruction handed over at start that cannot be read is set aside quietly, as the restore promises.

    The application starts with nothing open and says nothing; Reconstruction ▸ Open then opens a
    sound reconstruction, which shows the start left the application as usable as ever.
    """

    @pytest.fixture(params=STARTUP_CASES, ids=lambda case: case.name(""))
    def case(self, request: pytest.FixtureRequest) -> StartupCase:
        case: StartupCase = request.param
        return case

    @pytest.fixture
    def world(self) -> World:
        return broken_reconstruction_world()

    @pytest.fixture
    def startup(self, case: StartupCase) -> Startup:
        return Startup(reconstruction=RECONSTRUCTIONS_DIRECTORY / case.name(DOOR_SUFFIX_RECONSTRUCTION), project=None)

    def test_it_starts_with_nothing_open(self, screen: Screen, case: StartupCase) -> None:
        if case.damage is None:
            (RECONSTRUCTIONS_DIRECTORY / case.name(DOOR_SUFFIX_RECONSTRUCTION)).unlink(missing_ok=True)
        reconstructions = screen.reconstructions
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")
        screen.answer_next_dialog(DialogKind.OPEN, SECOND_RECONSTRUCTION)

        reconstructions.open_from_menu()

        screen.expect(
            lambda: reconstructions.shows_open(SECOND_RECONSTRUCTION),
            bool,
            description="the sound reconstruction open",
        )
        assert screen.shown_windows() == ()


ARCHIVE_DAMAGES: Final[Tuple[Damage, ...]] = (Damage.TRUNCATED, Damage.FOREIGN_BYTES)
VERSION_DAMAGES: Final[Tuple[Damage, ...]] = (Damage.OLDER_VERSION, Damage.FUTURE_VERSION)


def broken_project_world() -> World:
    return world_of(
        archived_document(ObjectKind.PROJECT, ARCHIVED_PROJECT),
        archived_document(ObjectKind.PROJECT, SECOND_PROJECT),
        *(damaged_project(damage) for damage in Damage),
    )


def open_project(screen: Screen, path: Path) -> None:
    """Chooses File ▸ Open project with ``path`` and lets the open project be replaced."""
    project = screen.project
    screen.answer_next_dialog(DialogKind.OPEN, path)
    project.open()
    screen.expect(project.replace_prompt.is_shown, bool, description="the question about replacing the project")
    project.replace_prompt.confirm()


def refused_project(screen: Screen, path: Path) -> str:
    """Reads the notice refusing ``path``, dismisses it, checks the project open before stands, and returns its words."""
    notice = shown_notice(screen)
    words = notice.words()
    screen.claim_error(path.name)

    notice.dismiss()

    screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")
    assert ARCHIVED_PROJECT.stem in screen.title()
    assert screen.sequencer.voices.names() == stored_voice_names()
    return words


def open_the_second_project_the_same_way(screen: Screen) -> None:
    open_project(screen, SECOND_PROJECT)

    screen.expect(lambda: SECOND_PROJECT.stem in screen.title(), bool, description="the second project open")


class TestRefusingABrokenProject:
    """A project that cannot be read is refused with a message naming why, and the one open stays open."""

    @pytest.fixture
    def world(self) -> World:
        return broken_project_world()

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=ARCHIVED_PROJECT)

    def test_a_damaged_or_missing_archive_is_refused_naming_the_file(self, screen: Screen) -> None:
        vanished = PROJECTS_DIRECTORY / f"{VANISHED}.stp"

        def refuse_each_damage(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            for damage in ARCHIVE_DAMAGES:
                path = PROJECTS_DIRECTORY / damaged_name(damage, DOOR_SUFFIX_PROJECT)
                open_project(screen, path)

                words = refused_project(screen, path)

                assert path.name in words

        def refuse_a_file_removed_after_it_was_chosen(screen: Screen) -> None:
            open_project(screen, vanished)

            words = refused_project(screen, vanished)

            assert vanished.name in words

        screen.scenario(
            refuse_each_damage,
            refuse_a_file_removed_after_it_was_chosen,
            open_the_second_project_the_same_way,
        ).run()

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a project at a version no step reaches is refused by its shape",
    )
    def test_a_version_no_step_reaches_is_refused_for_its_version(self, screen: Screen) -> None:
        screen.tabs.bring_to_front(Tab.SEQUENCER)
        for damage in VERSION_DAMAGES:
            path = PROJECTS_DIRECTORY / damaged_name(damage, DOOR_SUFFIX_PROJECT)
            open_project(screen, path)

            words = refused_project(screen, path)

            stated = stated_version(damage, SAMPLETONES_PROJECT_DATA_VERSION, OLDER_PROJECT_VERSION)
            assert stated in words and SAMPLETONES_PROJECT_DATA_VERSION in words, words


class TestABrokenProjectGivenAtStart:
    """A project handed over at start that cannot be read is set aside quietly, as the restore promises."""

    @pytest.fixture(params=STARTUP_CASES, ids=lambda case: case.name(""))
    def case(self, request: pytest.FixtureRequest) -> StartupCase:
        case: StartupCase = request.param
        return case

    @pytest.fixture
    def world(self) -> World:
        return broken_project_world()

    @pytest.fixture
    def startup(self, case: StartupCase) -> Startup:
        return Startup(reconstruction=None, project=PROJECTS_DIRECTORY / case.name(DOOR_SUFFIX_PROJECT))

    def test_it_starts_with_no_project_open(self, screen: Screen, case: StartupCase) -> None:
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")
        assert case.name(DOOR_SUFFIX_PROJECT) not in screen.title()
        screen.answer_next_dialog(DialogKind.OPEN, SECOND_PROJECT)

        screen.project.open()

        screen.expect(lambda: SECOND_PROJECT.stem in screen.title(), bool, description="the second project open")
        assert screen.shown_windows() == ()


OUTDATED_ROW: Final[str] = "instructions.library.template.library_node_outdated_template"
LIBRARY_LOADED: Final[str] = "instructions.library.template.library_loaded_template"
REBUILD_TIMEOUT_SECONDS: Final[float] = 300.0


def archived_library_path() -> Path:
    """Where the archived library lies in the library folder, under the name its settings give a library file."""
    document = stored_document(archived(ObjectKind.LIBRARY, ARCHIVED_VERSIONS[ObjectKind.LIBRARY]))
    config = Config(library=InstructionsLibraryConfig.model_validate(document[CONFIG_FIELD]))
    key = InstructionLibraryKey.create(config.library, Window.from_config(config))
    return LIBRARY_DIRECTORY / key.filename


class TestTheLastReleasesLibrary:
    """A library the last release built reads as out of date, and only a rebuild the user asks for replaces it."""

    @pytest.fixture
    def world(self) -> World:
        return world_of(archived_document(ObjectKind.LIBRARY, archived_library_path()))

    def test_cancel_leaves_it_and_rebuild_rebuilds_it_in_place(self, screen: Screen) -> None:
        library = screen.instructions.library
        path = archived_library_path()
        archived_bytes = path.read_bytes()
        outdated_mark = screen.words(OUTDATED_ROW).format("")

        def library_row() -> Item:
            return screen.expect_item(lambda: library.row(path.name), description="the library's row")

        def reads_out_of_date(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

            assert library.tree.label(library_row()).startswith(outdated_mark)

        def cancel_leaves_it(screen: Screen) -> None:
            prompt = library.rebuild_prompt
            library.tree.open_by_click(library_row())
            screen.expect(prompt.is_shown, bool, description="the rebuild question")

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            row = library_row()
            if library.tree.is_open(row):
                library.tree.open_by_click(row)
                screen.expect(lambda: library.tree.is_open(row), operator.not_, description="the row closed")
            library.tree.open_by_click(row)
            screen.expect(prompt.is_shown, bool, description="the rebuild question asked at the next opening")
            assert path.read_bytes() == archived_bytes

        def rebuild_replaces_it_in_place(screen: Screen) -> None:
            name = library.tree.label(library_row()).removeprefix(outdated_mark)

            library.rebuild_prompt.confirm()

            screen.bridge.expect(
                library.status,
                screen.words(LIBRARY_LOADED).format(name).__eq__,
                description="the rebuilt library loaded",
                timeout=REBUILD_TIMEOUT_SECONDS,
            )
            assert library.tree.label(library_row()) == name
            assert stored_version(ObjectKind.LIBRARY, path) == SAMPLETONES_LIBRARY_DATA_VERSION
            assert sorted(LIBRARY_DIRECTORY.glob(f"*{path.suffix}")) == [path]

        screen.scenario(reads_out_of_date, cancel_leaves_it, rebuild_replaces_it_in_place).run()


UNKNOWN_CARD: Final[str] = "main.retired.panel"
GONE_FOLDER: Final[str] = "Gone"
LIBRARIES_FOLDER: Final[str] = "Libraries"
VIEWPORT_FIELD: Final[str] = "viewport"
WIDTH_FIELD: Final[str] = "width"
WRONG_KIND_OF_WIDTH: Final[str] = "wide"
GENERAL_FIELD: Final[str] = "general"
MISSING_SETTING: Final[str] = "max_workers"


def state_from_elsewhere() -> bytes:
    """A session another build left: it names a card and a folder this home lacks, and a width in words."""
    state = screen_filling_state().model_copy(
        update={
            "advanced_settings": True,
            "current": Current(tab=Tab.SEQUENCER),
            "collapsed_cards": {UNKNOWN_CARD: True},
            "expanded_directories": [Path.cwd() / GONE_FOLDER],
        }
    )
    document = state.model_dump(mode="json")
    document[VIEWPORT_FIELD][WIDTH_FIELD] = WRONG_KIND_OF_WIDTH
    return yaml.safe_dump(document).encode()


def config_from_elsewhere() -> bytes:
    """Reconstruction settings another build left: they name a library folder and lack a setting."""
    config = Config()
    general = config.general.model_copy(update={"library_directory": str(Path.cwd() / LIBRARIES_FOLDER)})
    document = config.model_copy(update={"general": general}).model_dump(mode="json")
    del document[GENERAL_FIELD][MISSING_SETTING]
    return json.dumps(document).encode()


class TestSessionFilesFromElsewhere:
    """A session naming what this home lacks, with a setting of the wrong kind, beside settings missing one.

    The application starts without a word, and every setting the files name in a form this build
    reads applies.
    """

    @pytest.fixture
    def world(self) -> World:
        return World(
            state=None,
            application_config=None,
            config=None,
            files=(
                WrittenBytes(APPLICATION_STATE_PATH, state_from_elsewhere()),
                WrittenBytes(CONFIG_PATH, config_from_elsewhere()),
                Recording(Path.cwd() / LIBRARIES_FOLDER / "kick.wav", RECORDING_SECONDS, RECORDING_FREQUENCY),
            ),
        )

    def test_it_starts_without_a_word_and_applies_what_it_reads(self, screen: Screen) -> None:
        screen.expect(screen.tabs.front, Tab.SEQUENCER.__eq__, description="the Sequencer tab in front")

        assert screen.shown_windows() == ()
        assert screen.main.advanced.is_shown()
        assert screen.main.library_directory() == str(Path.cwd() / LIBRARIES_FOLDER)
