import operator
from pathlib import Path
from typing import Final, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_shared.application import SAMPLETONES_PROJECT_DATA_VERSION
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.screens.application.old_files.cases import STARTUP_CASES, StartupCase
from tests.screens.application.old_files.constants import ARCHIVED_PROJECT, VANISHED
from tests.screens.application.old_files.steps import (
    damaged_name,
    future_version,
    shown_notice,
    stated_version,
    stored_voice_names,
    world_of,
)
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.archives import Damage, archived_document, damaged_document
from tests.suite.screens.worlds.home import HomeFile, World

SECOND_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Second.stp"
OLDER_PROJECT_VERSION: Final[str] = "0.9"
DOOR_SUFFIX_PROJECT: Final[str] = ".stp"
ARCHIVE_DAMAGES: Final[Tuple[Damage, ...]] = (Damage.TRUNCATED, Damage.FOREIGN_BYTES)
VERSION_DAMAGES: Final[Tuple[Damage, ...]] = (Damage.OLDER_VERSION, Damage.FUTURE_VERSION)


def damaged_project(damage: Damage) -> HomeFile:
    """A damaged project file in the projects folder, one for each kind of ``damage``."""
    return damaged_document(
        ObjectKind.PROJECT,
        damage,
        destination=PROJECTS_DIRECTORY / damaged_name(damage, ".stp"),
        older_version=OLDER_PROJECT_VERSION,
        future_version=future_version(SAMPLETONES_PROJECT_DATA_VERSION),
    )


def broken_project_world() -> World:
    """A home with two sound projects, a damaged project for each damage, and a session."""
    return world_of(
        archived_document(ObjectKind.PROJECT, ARCHIVED_PROJECT),
        archived_document(ObjectKind.PROJECT, SECOND_PROJECT),
        *(damaged_project(damage) for damage in Damage),
    )


def open_project(screen: Screen, path: Path) -> None:
    """Chooses File > Open project with ``path`` and lets the open project be replaced."""
    project = screen.project
    screen.answer_next_dialog(DialogKind.OPEN, path)
    project.open()
    screen.expect(project.replace_prompt.is_shown, bool, description="the question about replacing the project")
    project.replace_prompt.confirm()


def refused_project(screen: Screen, path: Path) -> str:
    """Reads the notice refusing ``path``, dismisses it, checks the project open before stays open, and
    returns the words.
    """
    notice = shown_notice(screen)
    words = notice.words()
    screen.claim_error(path.name)

    notice.dismiss()

    screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")
    assert ARCHIVED_PROJECT.stem in screen.title()
    assert screen.sequencer.voices.names() == stored_voice_names()
    return words


def open_the_second_project_the_same_way(screen: Screen) -> None:
    """Opens the second sound project through the same menu and waits for its title."""
    open_project(screen, SECOND_PROJECT)

    screen.expect(lambda: SECOND_PROJECT.stem in screen.title(), bool, description="the second project open")


class TestRefusingABrokenProject:
    """A project that cannot be read is refused with a message naming why, and the one open stays open.

    The archived project is open at start. Each damaged or vanished file is chosen from File > Open
    project, and the notice names the file. A final open of a sound project succeeds, which shows the menu
    still works.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds sound projects and a damaged project for each kind of damage."""
        return broken_project_world()

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the archived project at start."""
        return Startup(reconstruction=None, project=ARCHIVED_PROJECT)

    def test_a_damaged_or_missing_archive_is_refused_naming_the_file(self, screen: Screen) -> None:
        """The notice names the file for each damaged archive and for a file removed after it was chosen."""
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

    def test_a_version_no_step_reaches_is_refused_for_its_version(self, screen: Screen) -> None:
        """The notice states the file's version and the current version."""
        screen.tabs.bring_to_front(Tab.SEQUENCER)
        for damage in VERSION_DAMAGES:
            path = PROJECTS_DIRECTORY / damaged_name(damage, DOOR_SUFFIX_PROJECT)
            open_project(screen, path)

            words = refused_project(screen, path)

            stated = stated_version(damage, SAMPLETONES_PROJECT_DATA_VERSION, OLDER_PROJECT_VERSION)
            assert stated in words and SAMPLETONES_PROJECT_DATA_VERSION in words, words


class TestABrokenProjectGivenAtStart:
    """A project handed over at start that cannot be read is set aside quietly, as the restore promises.

    The application starts on the Main tab with that project absent from the title. File > Open project
    then opens a sound project, with no window left shown.
    """

    @pytest.fixture(params=STARTUP_CASES, ids=lambda case: case.name(""))
    def case(self, request: pytest.FixtureRequest) -> StartupCase:
        """One row for each kind of damage, and one for a file that is gone."""
        case: StartupCase = request.param
        return case

    @pytest.fixture
    def world(self) -> World:
        """The home holds sound projects and a damaged project for each kind of damage."""
        return broken_project_world()

    @pytest.fixture
    def startup(self, case: StartupCase) -> Startup:
        """The application is handed the row's project at start."""
        return Startup(reconstruction=None, project=PROJECTS_DIRECTORY / case.name(DOOR_SUFFIX_PROJECT))

    def test_it_starts_with_no_project_open(self, screen: Screen, case: StartupCase) -> None:
        """The application starts with no project open and opens a sound one afterwards."""
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")
        assert case.name(DOOR_SUFFIX_PROJECT) not in screen.title()
        screen.answer_next_dialog(DialogKind.OPEN, SECOND_PROJECT)

        screen.project.open()

        screen.expect(lambda: SECOND_PROJECT.stem in screen.title(), bool, description="the second project open")
        assert screen.shown_windows() == ()
