import operator
from pathlib import Path
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.steps.sequencer import open_voice_menu
from automation.vocabulary.exports import EXPORT_INSTRUMENT, NSF_EXPORTED
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_player.specification.nsf import NSF_MAGIC
from sampletones_shared.paths.extensions import EXT_FILE_BITPHASE, EXT_FILE_MODULE, EXT_FILE_NSF
from tests.screens.exports.progress.constants import FAILED_EXPORT, INSTRUMENT_CHANNEL, MODULE_EXPORTED
from tests.screens.exports.progress.steps import folder, written_project
from tests.suite.screens.worlds.songs import LINE, OVERLONG_PROJECT, TWO_TUNINGS_PROJECT

NSF_FAILED: Final[str] = "global.dialog.message.nsf_project_export_failed"
BITPHASE_FAILED: Final[str] = "global.dialog.message.bitphase_project_export_failed"
INSTRUMENT_FAILED: Final[str] = "reconstructions.instruments.message.export_instrument_failed"
STORED_TICK_BY_TICK: Final[str] = "settings.nsf.label.scheme_none"
EVERY_REPEAT_ONCE: Final[str] = "settings.nsf.label.scheme_search"


def refused(screen: Screen, failed_key: str, destination: Path) -> None:
    """Waits for the error naming the export ``failed_key`` words, and checks that ``destination`` is still absent."""
    notice = screen.error_notice
    screen.expect(notice.is_shown, bool, description="the export refused")
    screen.claim_error(FAILED_EXPORT)
    assert screen.words(failed_key) in notice.words()
    assert not destination.exists()
    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the error gone")


def export_the_program(screen: Screen, level_key: str, destination: Path) -> None:
    """Opens File > Export > NSF program..., picks the level ``level_key`` words and the file, and presses Export."""
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
    """A song stored tick by tick that outgrows the room of an NSF program is refused with a message and the file
    stays absent; stored with each repeat saved once, it is written.
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
    """A project whose samples were converted at two tunings stops a song that sounds one tuning with a message and
    writes no file; a module, which keeps each sample's own pitches, is written.
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

    def test_an_instrument_export_stops_with_a_message(self, screen: Screen) -> None:
        """Export instrument... on a sample says the instrument failed and asks for no file."""
        notice = screen.error_notice
        asked = len(screen.dialog_requests())
        open_voice_menu(screen, LINE)

        screen.context_menu.choose_in(
            screen.words(EXPORT_INSTRUMENT),
            screen.channel_words(INSTRUMENT_CHANNEL),
        )

        screen.expect(notice.is_shown, bool, description="the export refused with a message")
        assert screen.words(INSTRUMENT_FAILED) in notice.words()
        assert len(screen.dialog_requests()) == asked
        notice.dismiss()
        screen.expect(notice.is_shown, operator.not_, description="the error gone")
