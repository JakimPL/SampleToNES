import operator
from functools import partial
from pathlib import Path
from typing import Final, Optional, Type

import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.worlds.home import HomeFile, World
from sampletones_application.categories.hierarchy import Tab
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_shared.application import SAMPLETONES_RECONSTRUCTION_DATA_VERSION
from sampletones_shared.exceptions.reconstruction import (
    IncompatibleReconstructionVersionError,
    InvalidReconstructionValuesError,
)
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.screens.application.old_files.cases import STARTUP_CASES, StartupCase
from tests.screens.application.old_files.constants import ARCHIVED_RECONSTRUCTION, BY_CONFIGURATION, VANISHED
from tests.screens.application.old_files.steps import (
    damaged_name,
    future_version,
    shown_notice,
    stated_version,
    world_of,
)
from tests.suite.screens.seeds.archives import Damage, archived_document, damaged_document
from tests.suite.screens.seeds.recordings import stored_recording

SECOND_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Second.stn"
OLDER_RECONSTRUCTION_VERSION: Final[str] = "2.0"
INVALID_VALUES: Final[str] = "reconstructions.browser.message.invalid_values"
INCOMPATIBLE_VERSION: Final[str] = "reconstructions.browser.template.incompatible_version_template"
RECONSTRUCTION_NOT_FOUND: Final[str] = "reconstructions.browser.message.file_not_found"
DOOR_SUFFIX_RECONSTRUCTION: Final[str] = ".stn"


def damaged_reconstruction(damage: Damage) -> HomeFile:
    """A damaged reconstruction file in the reconstructions folder for ``damage``."""
    return damaged_document(
        ObjectKind.RECONSTRUCTION,
        damage,
        destination=RECONSTRUCTIONS_DIRECTORY / damaged_name(damage, ".stn"),
        older_version=OLDER_RECONSTRUCTION_VERSION,
        future_version=future_version(SAMPLETONES_RECONSTRUCTION_DATA_VERSION),
    )


def reconstruction_refusal(screen: Screen, damage: Damage) -> str:
    """The words the application uses to refuse a reconstruction with ``damage``, as the language file has
    them.
    """
    match damage:
        case Damage.OLDER_VERSION | Damage.FUTURE_VERSION:
            stated = stated_version(damage, SAMPLETONES_RECONSTRUCTION_DATA_VERSION, OLDER_RECONSTRUCTION_VERSION)
            return screen.words(INCOMPATIBLE_VERSION).format(stated, SAMPLETONES_RECONSTRUCTION_DATA_VERSION)
        case Damage.TRUNCATED | Damage.FOREIGN_BYTES:
            return screen.words(INVALID_VALUES)


def reconstruction_failure(damage: Optional[Damage]) -> Type[BaseException]:
    """The failure type the application records for a reconstruction with ``damage``, or for a file that is
    gone.
    """
    match damage:
        case Damage.OLDER_VERSION | Damage.FUTURE_VERSION:
            return IncompatibleReconstructionVersionError
        case Damage.TRUNCATED | Damage.FOREIGN_BYTES:
            return InvalidReconstructionValuesError
        case None:
            return FileNotFoundError


def broken_reconstruction_world() -> World:
    """A home with sound reconstructions, a recording, and a damaged reconstruction for each damage."""
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
    """Reads the notice refusing a reconstruction, dismisses it, and checks the reconstruction open before
    stays open.
    """
    notice = shown_notice(screen)
    words = notice.words()
    screen.claim_error(reconstruction_failure(damage).__name__)

    notice.dismiss()

    screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")
    assert words.startswith(expected), words
    assert screen.reconstructions.shows_open(ARCHIVED_RECONSTRUCTION)


class TestRefusingABrokenReconstruction:
    """A reconstruction that cannot be read is refused with a readable message, and the one open stays open.

    Each door that opens a reconstruction is walked with every kind of damage, and then with a file removed
    after it was listed or chosen. The last gesture opens a sound reconstruction the same way, which shows
    the door still opens what it should.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds sound reconstructions and a damaged one for each kind of damage."""
        return broken_reconstruction_world()

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the archived reconstruction at start."""
        return Startup(reconstruction=ARCHIVED_RECONSTRUCTION, project=None)

    def test_through_the_browser(self, screen: Screen) -> None:
        """The door is a double click on a row of the reconstructions browser."""
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
        """The door is the Reconstruction > Open menu entry."""
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


class TestABrokenReconstructionGivenAtStart:
    """A reconstruction handed over at start that cannot be read is set aside quietly, as the restore
    promises.

    The application starts quietly with nothing open; Reconstruction > Open then opens a sound
    reconstruction, which shows the start left the application as usable as ever.
    """

    @pytest.fixture(params=STARTUP_CASES, ids=lambda case: case.name(""))
    def case(self, request: pytest.FixtureRequest) -> StartupCase:
        """One row for each kind of damage, and one for a file that is gone."""
        case: StartupCase = request.param
        return case

    @pytest.fixture
    def world(self) -> World:
        """The home holds sound reconstructions and a damaged one for each kind of damage."""
        return broken_reconstruction_world()

    @pytest.fixture
    def startup(self, case: StartupCase) -> Startup:
        """The application is handed the row's reconstruction at start."""
        return Startup(reconstruction=RECONSTRUCTIONS_DIRECTORY / case.name(DOOR_SUFFIX_RECONSTRUCTION), project=None)

    def test_it_starts_with_nothing_open(self, screen: Screen, case: StartupCase) -> None:
        """No window shows, and a sound reconstruction opens afterwards."""
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
