import operator
from pathlib import Path
from typing import Final, List, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.exports.instruments.import_files.constants import KEPT, VOICES
from tests.screens.exports.instruments.import_files.steps import choose_import, export_kept, segments
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.exports import leaving_asks_nothing
from tests.suite.screens.steps.sequencer import open_voice
from tests.suite.screens.views.history import HistorySegment
from tests.suite.screens.worlds.songs import PAD, RELEASING_INSTRUMENT, releasing_instrument

IMPORT_TITLE: Final[str] = "sequencer.voices.title.import_instrument_dialog"
NO_PROJECT_TITLE: Final[str] = "global.dialog.title.no_project_open"
NO_PROJECT_MESSAGE: Final[str] = "global.dialog.message.no_project_open"
IMPORTED_TITLE: Final[str] = "sequencer.voices.title.instrument_imported"
IMPORTED_TEMPLATE: Final[str] = "sequencer.voices.template.instrument_omissions"
RELEASE_POINT: Final[str] = "sequencer.voices.label.omission_release_point"
INSTRUMENT_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
SETTLING_FRAMES: Final[int] = 20


class TestImportWithNoProjectOpen:
    """Import instrument... with no project open says so and asks for no file; with a project open, it asks
    for one.

    The project is closed, Import instrument... is chosen on the list's menu, and a notice says that no
    project is open while the file dialog stays closed. A new project is created, and the same choice
    now asks for a file and shows no notice.
    """

    def test_it_says_so_and_asks_for_no_file(self, screen: Screen) -> None:
        """The notice appears with no project; with a new project the open dialog appears and the list stays
        empty.
        """
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
    """An instrument exported and imported again: the dialog opens where it was written, Cancel keeps
    everything as it was, and the import adds one voice playing the same envelopes, with no notice,
    which one undo takes away.

    The hand-written voice is exported from its menu. Cancel on the open dialog leaves the voices and
    the history as they were. Choosing the exported file adds the voice and one history line. The new
    voice shows the envelopes of the original, and one undo removes it.
    """

    def test_the_round_trip(self, screen: Screen) -> None:
        """The imported voice joins the list quietly, plays the same envelopes and goes with one undo."""
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
    """A FamiTracker instrument stating a release point imports, and a notice names the release point.

    The file is chosen on the import dialog. The voice joins the list and the notice names the
    instrument and the release point. Undo removes the voice.
    """

    def test_the_notice_names_what_it_left(self, screen: Screen) -> None:
        """The imported voice is listed and the notice names the release point that the import set aside."""
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
