import operator
from typing import Final

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_core.constants.enums import ChannelName
from sampletones_player.specification.nsf import NSF_MAGIC
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from tests.screens.exports.nsf_window.constants import LEFT_OUT, SETTLING_FRAMES
from tests.screens.exports.nsf_window.steps import folder
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION

INSTRUMENTS_EXPORTED: Final[str] = "reconstructions.instruments.message.export_instruments_success"
SILENT_IN_THE_RECONSTRUCTION: Final[ChannelName] = ChannelName.PULSE2


class TestAReconstructionsSilentChannels:
    """The NSF window of a reconstruction offers only the channels it sounds; a press on a silent channel's greyed
    box leaves it unticked.

    The scenario opens the window, presses the silent channel, unticks and ticks a sounding one, and writes the
    program, which starts with the NSF signature.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_a_silent_channel_stays_out(self, screen: Screen) -> None:
        window = screen.exports.nsf
        destination = folder("reconstruction") / f"{PLAYABLE_RECONSTRUCTION.stem}{EXT_FILE_NSF}"
        sounding = [channel for channel in ChannelName.items() if channel != SILENT_IN_THE_RECONSTRUCTION]

        def open_the_window(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)

            screen.exports.export_reconstruction(MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_NSF)

            screen.expect(window.is_shown, bool, description="the NSF window")
            assert not window.offers(SILENT_IN_THE_RECONSTRUCTION)
            assert not window.is_ticked(SILENT_IN_THE_RECONSTRUCTION)
            assert all(window.offers(channel) and window.is_ticked(channel) for channel in sounding)

        def a_press_on_the_silent_channel_ticks_nothing(screen: Screen) -> None:
            window.press_on(SILENT_IN_THE_RECONSTRUCTION)

            screen.frames(SETTLING_FRAMES)
            assert not window.is_ticked(SILENT_IN_THE_RECONSTRUCTION)

        def a_press_on_a_sounding_channel_lets_it_go_and_back(screen: Screen) -> None:
            window.tick(LEFT_OUT)
            screen.expect(lambda: window.is_ticked(LEFT_OUT), operator.not_, description="the noise let go")

            window.tick(LEFT_OUT)

            screen.expect(lambda: window.is_ticked(LEFT_OUT), bool, description="the noise ticked again")
            assert not window.is_ticked(SILENT_IN_THE_RECONSTRUCTION)

        def the_program_is_written(screen: Screen) -> None:
            notice = screen.exports.file_notice
            screen.answer_next_dialog(DialogKind.SAVE, destination)
            window.browse()
            screen.expect(lambda: screen.dialog_requests()[-1].answer == destination, bool, description="the file")

            window.export()

            screen.expect(notice.is_shown, bool, description="the program written")
            assert screen.words(INSTRUMENTS_EXPORTED) in notice.words()
            assert destination.read_bytes().startswith(NSF_MAGIC)
            notice.dismiss()

        screen.scenario(
            open_the_window,
            a_press_on_the_silent_channel_ticks_nothing,
            a_press_on_a_sounding_channel_lets_it_go_and_back,
            the_program_is_written,
        ).run()
