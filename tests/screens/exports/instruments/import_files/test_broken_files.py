import operator
from pathlib import Path
from typing import Final, List, Tuple

from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.steps.exports import leaving_asks_nothing
from automation.views.history import HistorySegment
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT
from tests.screens.exports.instruments.import_files.cases import BROKEN_FILES, BrokenFile
from tests.screens.exports.instruments.import_files.constants import VOICES
from tests.screens.exports.instruments.import_files.steps import choose_import, export_kept, kept_folder, segments

NOT_FOUND: Final[str] = "sequencer.voices.message.instrument_not_found"


class TestABrokenInstrumentFile:
    """A file that is no instrument, a truncated one and a missing one each give a message naming the
    trouble, and leave the voices and the history as they stood.

    A whole instrument is exported first. Each broken file is then chosen on the import dialog, the
    message is read and dismissed, and the voices and the history match their state before the import.
    """

    def test_each_is_reported_and_changes_nothing(self, screen: Screen) -> None:
        """Each broken file is reported, and the voices and the history stay as they were."""
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
