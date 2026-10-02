import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Final, List, Tuple

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.general import TAG_GLOBAL_THEME_INPUT_WARNING
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exports.stage import ExportStage
from sampletones_core.formats.bitphase.specification.macros import MAX_MACRO_LENGTH
from sampletones_core.formats.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS
from sampletones_player.specification.nsf import NSF_MAGIC
from sampletones_shared.paths.extensions import (
    EXT_FILE_BITPHASE,
    EXT_FILE_INSTRUMENT,
    EXT_FILE_JSON,
    EXT_FILE_MODULE,
    EXT_FILE_NSF,
)
from tests.suite.bitphase import parse_btp
from tests.suite.famitracker import parse_ftm
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.keys import IMGUI_ESCAPE
from tests.suite.screens.holds import FIRST_REPORT, ExportHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.steps.sequencer import open_voice, open_voice_menu
from tests.suite.screens.views.notices import Notice
from tests.suite.screens.world import (
    ARRANGED_PROJECT,
    LINE,
    LONG_ENVELOPES_PROJECT,
    LONG_ITEMS,
    LONG_VOICE,
    MIDDLING_ITEMS,
    MIDDLING_VOICE,
    OVERLONG_PROJECT,
    PAD,
    PLAYABLE_RECONSTRUCTION,
    TWO_TUNINGS_PROJECT,
)

EXPORT_INSTRUMENT: Final[str] = "sequencer.voices.label.context_export_instrument"
STAGE_WORDS: Final[Dict[ExportStage, str]] = {
    ExportStage.WALKING: "settings.export.label.stage_walking",
    ExportStage.COMPRESSING: "settings.export.label.stage_compressing",
    ExportStage.WRITING: "settings.export.label.stage_writing",
}
SETTLING_FRAMES: Final[int] = 20
FAILED_EXPORT: Final[str] = "Failed to export to"
NSF_FAILED: Final[str] = "global.dialog.message.nsf_project_export_failed"
NSF_EXPORTED: Final[str] = "global.dialog.message.nsf_project_exported_successfully"
BITPHASE_FAILED: Final[str] = "global.dialog.message.bitphase_project_export_failed"
BITPHASE_EXPORTED: Final[str] = "global.dialog.message.bitphase_project_exported_successfully"
MODULE_EXPORTED: Final[str] = "global.dialog.message.project_exported_successfully"
MODULE_FAILED: Final[str] = "global.dialog.message.project_export_failed"
READ_ONLY: Final[int] = 0o555
WRITABLE: Final[int] = 0o755
SHORTENED_PROJECT: Final[str] = "global.dialog.template.export_truncated"
STORED_TICK_BY_TICK: Final[str] = "settings.nsf.label.scheme_none"
EVERY_REPEAT_ONCE: Final[str] = "settings.nsf.label.scheme_search"
TOO_LONG: Final[str] = "reconstructions.instruments.message.status_sequence_too_long"
KEPT_BY_FAMITRACKER: Final[str] = "reconstructions.instruments.template.kept_famitracker"
KEPT_BY_BITPHASE: Final[str] = "reconstructions.instruments.template.kept_bitphase"
KEPT_BY_PRESET: Final[str] = "reconstructions.instruments.template.kept_bitphase_preset"
KEPT_SEPARATOR: Final[str] = "reconstructions.instruments.template.kept_separator"
INSTRUMENT_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
ASIDE: Final[Point] = Point(x=0, y=0)


def folder(name: str) -> Path:
    """A folder of the home for one door's files, standing on the disk as a native dialog's answer does."""
    path = Path.cwd() / "exports" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def click_cancel(screen: Screen) -> None:
    screen.exports.progress.cancel()


def press_escape(screen: Screen) -> None:
    screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])


@dataclass(frozen=True)
class ExportDoor:
    """One way an export is started, what its window shows first, and how the reader cancels it.

    Attributes:
        name: The folder the door writes into, named after the door.
        start: Starts the export into the folder it is given, answering the dialogs it opens.
        first_stage: The stage the run reports first, which the window lists.
        cancel: The reader's way of canceling the run.
        project: Whether the export writes the project, whose outcome stands in the project's notice.
    """

    name: str
    start: Callable[[Screen, Path], None]
    first_stage: ExportStage
    cancel: Callable[[Screen], None]
    project: bool


def from_the_file_menu(item: MenuElements, extension: str) -> Callable[[Screen, Path], None]:
    def start(screen: Screen, into: Path) -> None:
        screen.answer_next_dialog(DialogKind.SAVE, into / f"{ARRANGED_PROJECT.stem}{extension}")
        screen.exports.export_project(item)

    return start


def from_the_reconstruction_menu(item: MenuElements, extension: str) -> Callable[[Screen, Path], None]:
    def start(screen: Screen, into: Path) -> None:
        screen.answer_next_dialog(DialogKind.SAVE, into / f"{PLAYABLE_RECONSTRUCTION.stem}{extension}")
        screen.exports.export_reconstruction(item)

    return start


def through_the_nsf_window(menu_start: Callable[[Screen], None], stem: str) -> Callable[[Screen, Path], None]:
    def start(screen: Screen, into: Path) -> None:
        window = screen.exports.nsf
        menu_start(screen)
        screen.expect(window.is_shown, bool, description="the NSF window")
        screen.answer_next_dialog(DialogKind.SAVE, into / f"{stem}{EXT_FILE_NSF}")
        window.browse()
        screen.expect(
            lambda: screen.dialog_requests()[-1].answer == into / f"{stem}{EXT_FILE_NSF}",
            bool,
            description="the file chosen",
        )
        window.export()

    return start


def from_the_voice_menu(screen: Screen, into: Path) -> None:
    screen.answer_next_dialog(DialogKind.SAVE, into / f"{PAD}{EXT_FILE_INSTRUMENT}")
    open_voice_menu(screen, PAD)
    screen.context_menu.choose(screen.words(EXPORT_INSTRUMENT))


PROJECT_DOORS: Final[Tuple[ExportDoor, ...]] = (
    ExportDoor(
        name="module",
        start=from_the_file_menu(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER, EXT_FILE_MODULE),
        first_stage=ExportStage.WRITING,
        cancel=click_cancel,
        project=True,
    ),
    ExportDoor(
        name="bitphase",
        start=from_the_file_menu(MenuElements.ITEM_FILE_EXPORT_BITPHASE, EXT_FILE_BITPHASE),
        first_stage=ExportStage.WRITING,
        cancel=press_escape,
        project=True,
    ),
    ExportDoor(
        name="program",
        start=through_the_nsf_window(
            lambda screen: screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_NSF),
            ARRANGED_PROJECT.stem,
        ),
        first_stage=ExportStage.WALKING,
        cancel=click_cancel,
        project=True,
    ),
)

INSTRUMENT_DOORS: Final[Tuple[ExportDoor, ...]] = (
    ExportDoor(
        name="instruments",
        start=from_the_reconstruction_menu(
            MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_FAMITRACKER,
            EXT_FILE_INSTRUMENT,
        ),
        first_stage=ExportStage.WRITING,
        cancel=click_cancel,
        project=False,
    ),
    ExportDoor(
        name="presets",
        start=from_the_reconstruction_menu(
            MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_BITPHASE_PRESET,
            EXT_FILE_JSON,
        ),
        first_stage=ExportStage.WRITING,
        cancel=press_escape,
        project=False,
    ),
    ExportDoor(
        name="sample program",
        start=through_the_nsf_window(
            lambda screen: screen.exports.export_reconstruction(
                MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_NSF
            ),
            PLAYABLE_RECONSTRUCTION.stem,
        ),
        first_stage=ExportStage.WALKING,
        cancel=click_cancel,
        project=False,
    ),
    ExportDoor(
        name="instrument",
        start=from_the_voice_menu,
        first_stage=ExportStage.WRITING,
        cancel=click_cancel,
        project=False,
    ),
)


def outcome_notice(screen: Screen, door: ExportDoor) -> Notice:
    return screen.exports.project_notice if door.project else screen.exports.file_notice


def canceled_and_then_written(screen: Screen, hold: ExportHold, door: ExportDoor) -> None:
    """Starts ``door``'s export under the hold, cancels it, and starts it again unheld, which writes."""
    progress = screen.exports.progress
    notice = outcome_notice(screen, door)
    into = folder(door.name)
    hold.hold_at(FIRST_REPORT)

    door.start(screen, into)

    screen.expect(progress.is_shown, bool, description=f"the {door.name} export under way")
    screen.expect(hold.waiting, (1).__eq__, description=f"the {door.name} export held")
    assert progress.stages() == (screen.words(STAGE_WORDS[door.first_stage]),)

    door.cancel(screen)

    screen.expect(progress.is_shown, operator.not_, description=f"the {door.name} export canceled")
    screen.frames(SETTLING_FRAMES)
    assert hold.waiting() == 0
    assert not notice.is_shown()
    assert list(into.iterdir()) == []

    hold.release()
    door.start(screen, into)

    screen.expect(notice.is_shown, bool, description=f"the {door.name} export written")
    assert not progress.is_shown()
    assert list(into.iterdir()) != []
    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the notice gone")


class TestEveryExportAnswersCancel:
    """Every export shows its window while it runs and stops at a cancel with no file written; let run, it writes.

    Cancel is clicked on some doors and Escape pressed on others.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)

    def test_the_project_exports(self, screen: Screen, export_hold: ExportHold) -> None:
        def each_project_export(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            for door in PROJECT_DOORS:
                canceled_and_then_written(screen, export_hold, door)

        screen.scenario(each_project_export).run()

    def test_the_instrument_exports(self, screen: Screen, export_hold: ExportHold) -> None:
        def each_instrument_export(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            for door in INSTRUMENT_DOORS:
                canceled_and_then_written(screen, export_hold, door)

        screen.scenario(each_instrument_export).run()


def refused(screen: Screen, failed_key: str, destination: Path) -> None:
    """Waits for the error naming the export ``failed_key`` words, and checks nothing was written to ``destination``."""
    notice = screen.error_notice
    screen.expect(notice.is_shown, bool, description="the export refused")
    screen.claim_error(FAILED_EXPORT)
    assert screen.words(failed_key) in notice.words()
    assert not destination.exists()
    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the error gone")


def written_project(screen: Screen, exported_key: str, destination: Path) -> str:
    """Waits for the notice of the project export ``exported_key`` words, dismisses it, and answers what it said."""
    notice = screen.exports.project_notice
    screen.expect(notice.is_shown, bool, description=f"{destination.name} written")
    words = notice.words()
    assert screen.words(exported_key) in words
    assert destination.is_file()
    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the notice gone")
    return words


def export_the_program(screen: Screen, level_key: str, destination: Path) -> None:
    """Opens File ▸ Export ▸ NSF program..., picks the level ``level_key`` words and the file, and presses Export."""
    window = screen.exports.nsf
    screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_NSF)
    screen.expect(window.is_shown, bool, description="the NSF window")
    window.choose_level(screen.words(level_key))
    screen.answer_next_dialog(DialogKind.SAVE, destination)
    window.browse()
    screen.expect(lambda: screen.dialog_requests()[-1].answer == destination, bool, description="the file chosen")
    assert window.level() == screen.words(level_key)

    window.export()


class TestASongTooLargeForTheProgram:
    """A song stored tick by tick past the room an NSF program has is refused with a message, and nothing is written;
    stored with each repeat saved once, it is written.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=OVERLONG_PROJECT)

    def test_it_is_refused_and_then_fits(self, screen: Screen) -> None:
        destination = folder("overlong") / f"{OVERLONG_PROJECT.stem}{EXT_FILE_NSF}"

        def stored_tick_by_tick_it_is_refused(screen: Screen) -> None:
            export_the_program(screen, STORED_TICK_BY_TICK, destination)

            refused(screen, NSF_FAILED, destination)

        def saving_each_repeat_once_it_is_written(screen: Screen) -> None:
            export_the_program(screen, EVERY_REPEAT_ONCE, destination)

            written_project(screen, NSF_EXPORTED, destination)
            assert destination.read_bytes().startswith(NSF_MAGIC)

        screen.scenario(stored_tick_by_tick_it_is_refused, saving_each_repeat_once_it_is_written).run()


class TestTwoTunings:
    """A project whose samples were converted at two tunings: a song sounding one tuning stops with a message and
    writes nothing, and a module, which keeps each sample's own pitches, is written.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=TWO_TUNINGS_PROJECT)

    def test_a_song_sounding_one_tuning_stops(self, screen: Screen) -> None:
        into = folder("tunings")

        def a_bitphase_project_stops(screen: Screen) -> None:
            destination = into / f"{TWO_TUNINGS_PROJECT.stem}{EXT_FILE_BITPHASE}"
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_BITPHASE)

            refused(screen, BITPHASE_FAILED, destination)

        def a_program_stops(screen: Screen) -> None:
            destination = into / f"{TWO_TUNINGS_PROJECT.stem}{EXT_FILE_NSF}"

            export_the_program(screen, EVERY_REPEAT_ONCE, destination)

            refused(screen, NSF_FAILED, destination)

        def a_module_is_written(screen: Screen) -> None:
            destination = into / f"{TWO_TUNINGS_PROJECT.stem}{EXT_FILE_MODULE}"
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER)

            written_project(screen, MODULE_EXPORTED, destination)

        screen.scenario(a_bitphase_project_stops, a_program_stops, a_module_is_written).run()

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: Export instrument... in a project of two tunings fails with no message",
    )
    def test_an_instrument_export_stops_with_a_message(self, screen: Screen) -> None:
        open_voice_menu(screen, LINE)

        screen.context_menu.choose_in(
            screen.words(EXPORT_INSTRUMENT),
            screen.channel_words(INSTRUMENT_CHANNEL),
        )

        screen.expect(screen.error_notice.is_shown, bool, description="the export refused with a message")


def written_for(names: List[str], voices: Tuple[str, ...]) -> int:
    """How many of the instruments a file lists under ``names`` were written for one of ``voices``."""
    return sum(1 for name in names if any(name == voice or name.startswith(f"{voice} (") for voice in voices))


class TestShortenedEnvelopes:
    """An envelope longer than a format stores: its field's status names each export that cuts it and what each keeps,
    and a project export says how many of the instruments it wrote it shortened.

    The long voice runs past every format's limit, and the middling one past FamiTracker's alone. A format writes a
    voice as one instrument or several, so the count the notice gives is read against the instruments the file lists.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=LONG_ENVELOPES_PROJECT)

    def test_the_status_and_the_notices_name_the_cuts(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        into = folder("shortened")

        def status_of(voice: str) -> str:
            open_voice(screen, voice)
            screen.expect(
                lambda: instruments.tab_label(INSTRUMENT_CHANNEL),
                voice.__eq__,
                description=f"{voice} open",
            )
            screen.hand.move_to(ASIDE)
            instruments.hover_field(INSTRUMENT_CHANNEL, FeatureKey.VOLUME)
            return screen.expect(screen.status, bool, description=f"the status of {voice}'s volume")

        def too_long(items: int, *kept: str) -> str:
            return screen.words(TOO_LONG).format(
                instrument_feature=FeatureKey.VOLUME.capitalized,
                items=items,
                kept=screen.words(KEPT_SEPARATOR).join(kept),
            )

        def the_long_voice_names_every_format(screen: Screen) -> None:
            status = status_of(LONG_VOICE)

            assert status == too_long(
                LONG_ITEMS,
                screen.words(KEPT_BY_FAMITRACKER).format(limit=MAX_SEQUENCE_ITEMS),
                screen.words(KEPT_BY_BITPHASE).format(limit=MAX_MACRO_LENGTH),
                screen.words(KEPT_BY_PRESET).format(limit=MAX_MACRO_LENGTH),
            )
            assert instruments.field_theme(INSTRUMENT_CHANNEL, FeatureKey.VOLUME) == TAG_GLOBAL_THEME_INPUT_WARNING

        def the_middling_voice_names_famitracker_alone(screen: Screen) -> None:
            status = status_of(MIDDLING_VOICE)

            assert status == too_long(
                MIDDLING_ITEMS,
                screen.words(KEPT_BY_FAMITRACKER).format(limit=MAX_SEQUENCE_ITEMS),
            )

        def a_bitphase_project_shortens_one(screen: Screen) -> None:
            destination = into / f"{LONG_ENVELOPES_PROJECT.stem}{EXT_FILE_BITPHASE}"
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_BITPHASE)

            words = written_project(screen, BITPHASE_EXPORTED, destination)
            names = [instrument.name for instrument in parse_btp(destination.read_bytes(), []).instruments]
            assert (
                screen.words(SHORTENED_PROJECT).format(
                    instruments=written_for(names, (LONG_VOICE,)),
                    frames=MAX_MACRO_LENGTH,
                    source_frames=LONG_ITEMS,
                )
                in words
            )

        def a_module_shortens_both(screen: Screen) -> None:
            destination = into / f"{LONG_ENVELOPES_PROJECT.stem}{EXT_FILE_MODULE}"
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER)

            words = written_project(screen, MODULE_EXPORTED, destination)
            names = [instrument.name for instrument in parse_ftm(destination.read_bytes()).instruments]
            assert (
                screen.words(SHORTENED_PROJECT).format(
                    instruments=written_for(names, (LONG_VOICE, MIDDLING_VOICE)),
                    frames=MAX_SEQUENCE_ITEMS,
                    source_frames=LONG_ITEMS,
                )
                in words
            )

        screen.scenario(
            the_long_voice_names_every_format,
            the_middling_voice_names_famitracker_alone,
            a_bitphase_project_shortens_one,
            a_module_shortens_both,
        ).run()


class TestAnExportFailingUnderItsWindow:
    """An export failing while its window stands: the window goes, one error says what failed, and nothing is written;
    once the folder takes files again, the same export writes.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=ARRANGED_PROJECT)

    def test_the_error_follows_the_window(self, screen: Screen, export_hold: ExportHold) -> None:
        progress = screen.exports.progress
        into = folder("locked")
        destination = into / f"{ARRANGED_PROJECT.stem}{EXT_FILE_MODULE}"

        def start_the_module_export(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER)

            screen.expect(progress.is_shown, bool, description="the export under way")
            screen.expect(export_hold.waiting, (1).__eq__, description="the export held")

        def the_folder_refuses_the_file(screen: Screen) -> None:
            into.chmod(READ_ONLY)
            try:
                export_hold.release()

                screen.expect(screen.error_notice.is_shown, bool, description="the export failed")
            finally:
                into.chmod(WRITABLE)

            screen.claim_error(FAILED_EXPORT)
            assert not progress.is_shown()
            standing = screen.error_notice.prompt.window()
            assert standing is not None
            assert [window.alias for window in screen.shown_windows()] == [standing.alias]
            assert screen.words(MODULE_FAILED) in screen.error_notice.words()
            assert list(into.iterdir()) == []
            screen.error_notice.dismiss()
            screen.expect(screen.error_notice.is_shown, operator.not_, description="the error gone")

        def the_same_export_then_writes(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER)

            written_project(screen, MODULE_EXPORTED, destination)

        screen.scenario(start_the_module_export, the_folder_refuses_the_file, the_same_export_then_writes).run()
