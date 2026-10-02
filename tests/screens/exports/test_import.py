import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import forgive_the_hover_race, open_voice, open_voice_menu
from tests.suite.screens.views.history import HistoryLine, HistorySegment
from tests.suite.screens.world import (
    ARRANGED_PROJECT,
    BASS_VOICE,
    LINE,
    PAD,
    RELEASING_INSTRUMENT,
    releasing_instrument,
)

IMPORT_INSTRUMENT: Final[str] = "sequencer.voices.label.import_instrument"
IMPORT_TITLE: Final[str] = "sequencer.voices.title.import_instrument_dialog"
EXPORT_INSTRUMENT: Final[str] = "sequencer.voices.label.context_export_instrument"
NO_PROJECT_TITLE: Final[str] = "global.dialog.title.no_project_open"
NO_PROJECT_MESSAGE: Final[str] = "global.dialog.message.no_project_open"
IMPORTED_TITLE: Final[str] = "sequencer.voices.title.instrument_imported"
IMPORTED_TEMPLATE: Final[str] = "sequencer.voices.template.instrument_omissions"
RELEASE_POINT: Final[str] = "sequencer.voices.label.omission_release_point"
NOT_FOUND: Final[str] = "sequencer.voices.message.instrument_not_found"
READ_FAILED: Final[str] = "Failed to read an instrument from"
NO_FILE: Final[str] = "No instrument file at"
FOREIGN_BYTES: Final[bytes] = b"These bytes were written by another program and hold no instrument.\n"
KEPT: Final[str] = "Kept"
FOLDER: Final[str] = "kept"
VOICES: Final[List[str]] = [LINE, BASS_VOICE, PAD]
INSTRUMENT_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
SETTLING_FRAMES: Final[int] = 20
HALF: Final[int] = 2


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


def kept_folder() -> Path:
    path = Path.cwd() / FOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path


def choose_import(screen: Screen) -> None:
    """Chooses Import instrument... on the menu the empty foot of the voice list opens."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.sequencer.voices.right_click_below_the_rows()
    screen.expect(screen.context_menu.is_shown, bool, description="the list's menu")
    screen.context_menu.choose(screen.words(IMPORT_INSTRUMENT))


def export_kept(screen: Screen) -> Path:
    """Exports the hand-written voice from its menu to the kept folder under the name :data:`KEPT`."""
    path = kept_folder() / f"{KEPT}{EXT_FILE_INSTRUMENT}"
    notice = screen.exports.file_notice
    screen.answer_next_dialog(DialogKind.SAVE, path)
    open_voice_menu(screen, PAD)
    screen.context_menu.choose(screen.words(EXPORT_INSTRUMENT))
    screen.expect(notice.is_shown, bool, description="the notice of the export")
    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the notice gone")
    return path


def segments(lines: Tuple[HistoryLine, ...]) -> List[Tuple[HistorySegment, ...]]:
    return [tuple(line.segments) for line in lines]


def leaving_asks_nothing(screen: Screen) -> None:
    """Exits a project left as it was opened, which leaves at once."""
    forgive_the_hover_race(screen)
    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()


class TestImportWithNoProjectOpen:
    """Import instrument... with no project open says so and asks for no file; with a project open, it asks for one."""

    def test_it_says_so_and_asks_for_no_file(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        notice = voices.no_project_notice
        asked: List[int] = []

        def close_the_project(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)

            screen.project.close()

            screen.expect(voices.names, operator.not_, description="no voices listed")
            asked.append(len(screen.dialog_requests()))

        def import_says_no_project_is_open(screen: Screen) -> None:
            choose_import(screen)

            screen.expect(notice.is_shown, bool, description="the notice")
            assert notice.prompt.title() == screen.words(NO_PROJECT_TITLE)
            assert notice.words() == screen.words(NO_PROJECT_MESSAGE)
            assert len(screen.dialog_requests()) == asked[0]
            notice.dismiss()
            screen.expect(notice.is_shown, operator.not_, description="the notice gone")

        def with_a_new_project_it_asks_for_a_file(screen: Screen) -> None:
            screen.project.create()
            screen.answer_next_dialog(DialogKind.OPEN, None)

            choose_import(screen)

            screen.expect(
                lambda: len(screen.dialog_requests()),
                (asked[0] + 1).__eq__,
                description="the file asked for",
            )
            request = screen.dialog_requests()[-1]
            assert request.kind == DialogKind.OPEN
            assert request.title == screen.words(IMPORT_TITLE)
            assert not notice.is_shown()
            assert voices.names() == []

        screen.scenario(
            close_the_project,
            import_says_no_project_is_open,
            with_a_new_project_it_asks_for_a_file,
            leaving_asks_nothing,
        ).run()


class TestAnExportedVoiceComesBack:
    """An instrument exported and imported again: the dialog opens where it was written, Cancel changes nothing, and
    the import adds one voice playing the same envelopes, with no notice, which one undo takes away.
    """

    def test_the_round_trip(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        history = screen.sequencer.history
        instruments = screen.reconstructions.instruments
        exported: List[Path] = []
        before: List[List[Tuple[HistorySegment, ...]]] = []
        envelopes: List[Tuple[str, str]] = []

        def export_the_hand_written_voice(screen: Screen) -> None:
            open_voice(screen, PAD)
            screen.expect(instruments.offers_audition, bool, description="the hand-written voice open")
            envelopes.append(
                (
                    instruments.envelope(INSTRUMENT_CHANNEL, FeatureKey.VOLUME),
                    instruments.envelope(INSTRUMENT_CHANNEL, FeatureKey.ARPEGGIO),
                )
            )

            exported.append(export_kept(screen))

            before.append(segments(history.lines()))

        def cancel_changes_nothing(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, None)

            choose_import(screen)

            screen.expect(lambda: screen.dialog_requests()[-1].kind == DialogKind.OPEN, bool, description="asked")
            screen.frames(SETTLING_FRAMES)
            assert screen.dialog_requests()[-1].initial_directory == exported[0].parent
            assert voices.names() == VOICES
            assert segments(history.lines()) == before[0]

        def the_import_adds_the_voice_quietly(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, exported[0])

            choose_import(screen)

            screen.expect(voices.names, (VOICES + [KEPT]).__eq__, description="the voice imported")
            screen.frames(SETTLING_FRAMES)
            assert not voices.imported_notice.is_shown()
            assert len(history.lines()) == len(before[0]) + 1

        def it_plays_the_same_envelopes(screen: Screen) -> None:
            open_voice(screen, KEPT)

            screen.expect(
                lambda: instruments.tab_label(INSTRUMENT_CHANNEL),
                KEPT.__eq__,
                description="the imported voice open",
            )
            assert (
                instruments.envelope(INSTRUMENT_CHANNEL, FeatureKey.VOLUME),
                instruments.envelope(INSTRUMENT_CHANNEL, FeatureKey.ARPEGGIO),
            ) == envelopes[0]

        def one_undo_takes_it_away(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)

            history.undo()

            screen.expect(voices.names, VOICES.__eq__, description="the import undone")

        screen.scenario(
            export_the_hand_written_voice,
            cancel_changes_nothing,
            the_import_adds_the_voice_quietly,
            it_plays_the_same_envelopes,
            one_undo_takes_it_away,
            leaving_asks_nothing,
        ).run()


class TestAFileStatingMore:
    """A FamiTracker instrument stating a release point imports, and a notice names the release point."""

    def test_the_notice_names_what_it_left(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        notice = voices.imported_notice

        def import_it(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, releasing_instrument())

            choose_import(screen)

            screen.expect(notice.is_shown, bool, description="the notice")
            assert voices.names() == VOICES + [RELEASING_INSTRUMENT]
            assert notice.prompt.title() == screen.words(IMPORTED_TITLE)
            words = notice.words()
            assert screen.words(IMPORTED_TEMPLATE).format(name=RELEASING_INSTRUMENT) in words
            assert screen.words(RELEASE_POINT) in words
            notice.dismiss()

        def undo_and_leave(screen: Screen) -> None:
            screen.expect(notice.is_shown, operator.not_, description="the notice gone")
            screen.press_shortcut(ShortcutId.UNDO)
            screen.expect(voices.names, VOICES.__eq__, description="the import undone")

        screen.scenario(import_it, undo_and_leave, leaving_asks_nothing).run()


@dataclass(frozen=True)
class BrokenFile:
    """A file the import meets broken: how it is laid in the home, and what the application logs on meeting it."""

    name: str
    lay: Callable[[Path, Path], None]
    logged: str
    not_found: bool


def foreign(destination: Path, _exported: Path) -> None:
    destination.write_bytes(FOREIGN_BYTES)


def truncated(destination: Path, exported: Path) -> None:
    content = exported.read_bytes()
    destination.write_bytes(content[: len(content) // HALF])


def missing(_destination: Path, _exported: Path) -> None:
    """Lays nothing: the file is gone by the time the import reads it."""


BROKEN_FILES: Final[Tuple[BrokenFile, ...]] = (
    BrokenFile(name="Foreign", lay=foreign, logged=READ_FAILED, not_found=False),
    BrokenFile(name="Truncated", lay=truncated, logged=READ_FAILED, not_found=False),
    BrokenFile(name="Missing", lay=missing, logged=NO_FILE, not_found=True),
)


class TestABrokenInstrumentFile:
    """A file that is no instrument, a truncated one and a missing one each give a message naming the trouble, and
    leave the voices and the history as they stood.
    """

    def test_each_is_reported_and_changes_nothing(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        history = screen.sequencer.history
        exported: List[Path] = []
        before: List[List[Tuple[HistorySegment, ...]]] = []

        def export_a_whole_file(screen: Screen) -> None:
            exported.append(export_kept(screen))
            before.append(segments(history.lines()))

        def importing(broken: BrokenFile) -> None:
            path = kept_folder() / f"{broken.name}{EXT_FILE_INSTRUMENT}"
            broken.lay(path, exported[0])
            notice = screen.file_not_found_notice if broken.not_found else screen.error_notice
            screen.answer_next_dialog(DialogKind.OPEN, path)

            choose_import(screen)

            screen.expect(notice.is_shown, bool, description=f"the message about {broken.name}")
            screen.claim_error(broken.logged)
            if broken.not_found:
                assert screen.words(NOT_FOUND) in notice.words()
                assert str(path) in notice.words()

            notice.dismiss()
            screen.expect(notice.is_shown, operator.not_, description="the message gone")
            assert voices.names() == VOICES
            assert segments(history.lines()) == before[0]

        def import_each_broken_file(screen: Screen) -> None:
            for broken in BROKEN_FILES:
                importing(broken)

        screen.scenario(export_a_whole_file, import_each_broken_file, leaving_asks_nothing).run()
