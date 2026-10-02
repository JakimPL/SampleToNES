import operator
from pathlib import Path
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.formats.famitracker.instrument import read_fti
from sampletones_player.specification.nsf import NSF_MAGIC
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT, EXT_FILE_JSON, EXT_FILE_NSF
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.items import EntryReading
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, open_voice, open_voice_menu
from tests.suite.screens.world import ARRANGED_PROJECT, BASS_VOICE, LINE, PAD

EXPORT_INSTRUMENT: Final[str] = "sequencer.voices.label.context_export_instrument"
EXPORT_TITLE: Final[str] = "reconstructions.instruments.title.export_instrument_dialog"
EXPORTED: Final[str] = "reconstructions.instruments.message.export_instrument_success"
FAMITRACKER_TYPE: Final[str] = "global.dialog.filter.famitracker_instrument"
BITPHASE_PRESET_TYPE: Final[str] = "global.dialog.filter.bitphase_preset"
NSF_TYPE: Final[str] = "global.dialog.filter.nsf"
FTI_MAGIC: Final[bytes] = b"FTI"
JSON_OPENING: Final[bytes] = b"{"
LINE_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE)
INSTRUMENT_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
EMPTY: Final[str] = ""
RENAMED: Final[str] = "Renamed"
EXPORTS: Final[str] = "exports"


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


def folder(*parts: str) -> Path:
    """A folder of the home a save dialog can answer with, which stands on the disk as a native dialog's answer does."""
    path = Path.cwd().joinpath(EXPORTS, *parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_entry(screen: Screen) -> Optional[EntryReading]:
    """The plain Export instrument... entry of the open menu, if it offers one."""
    words = screen.words(EXPORT_INSTRUMENT)
    return next((entry for entry in screen.context_menu.entries() if entry.label == words), None)


def export_from_the_menu(screen: Screen, voice: str) -> None:
    """Chooses Export instrument... on the menu of ``voice``, a voice holding one instrument."""
    open_voice_menu(screen, voice)
    screen.context_menu.choose(screen.words(EXPORT_INSTRUMENT))


def written(screen: Screen, path: Path) -> None:
    """Waits for the notice naming the instrument file ``path`` written, and dismisses it."""
    notice = screen.exports.file_notice
    screen.expect(notice.is_shown, bool, description=f"the notice of {path.name}")
    words = notice.words()
    assert screen.words(EXPORTED) in words
    assert str(path) in words
    assert path.is_file()

    notice.dismiss()

    screen.expect(notice.is_shown, operator.not_, description="the notice gone")


def leaving_asks_nothing(screen: Screen) -> None:
    """Exits a project only exported from, which leaves at once: an export changes nothing in the project."""
    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()


class TestTheExportEntryFollowsWhatAVoiceHolds:
    """Export instrument... is one entry on a voice holding one instrument and a submenu of channels on a sample holding
    several; a voice holding none greys it, and greys the Reconstructions tab's button with it.
    """

    def test_one_entry_a_submenu_and_a_greyed_entry(self, screen: Screen) -> None:
        menu = screen.context_menu
        instruments = screen.reconstructions.instruments

        def a_hand_written_voice_offers_one_entry(screen: Screen) -> None:
            open_voice_menu(screen, PAD)

            entry = export_entry(screen)
            assert entry is not None
            assert entry.enabled
            assert screen.words(EXPORT_INSTRUMENT) not in menu.submenus()
            menu.dismiss()

        def a_sample_of_three_channels_names_each(screen: Screen) -> None:
            open_voice_menu(screen, LINE)

            assert export_entry(screen) is None
            assert menu.submenu(screen.words(EXPORT_INSTRUMENT)) == [
                (screen.channel_words(channel), True) for channel in LINE_CHANNELS
            ]
            menu.dismiss()

        def a_sample_of_one_channel_offers_one_entry(screen: Screen) -> None:
            open_voice_menu(screen, BASS_VOICE)

            entry = export_entry(screen)
            assert entry is not None
            assert entry.enabled
            assert screen.words(EXPORT_INSTRUMENT) not in menu.submenus()
            menu.dismiss()

        def a_voice_left_without_envelopes_greys_both(screen: Screen) -> None:
            open_voice(screen, PAD)
            screen.expect(instruments.offers_audition, bool, description="the hand-written voice open")
            assert instruments.can_export(INSTRUMENT_CHANNEL)

            for feature in (FeatureKey.VOLUME, FeatureKey.ARPEGGIO):
                instruments.type_envelope(INSTRUMENT_CHANNEL, feature, EMPTY)

            screen.expect(
                lambda: instruments.can_export(INSTRUMENT_CHANNEL),
                operator.not_,
                description="the button greyed",
            )
            open_voice_menu(screen, PAD)
            entry = export_entry(screen)
            assert entry is not None
            assert not entry.enabled
            menu.dismiss()

        screen.scenario(
            a_hand_written_voice_offers_one_entry,
            a_sample_of_three_channels_names_each,
            a_sample_of_one_channel_offers_one_entry,
            a_voice_left_without_envelopes_greys_both,
            leave_letting_the_project_go,
        ).run()


class TestEveryDoorWritesTheSameBytes:
    """The Reconstructions tab's button and the voice's menu write the same file for the same voice."""

    def test_the_button_and_the_menu_agree(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        through_the_button = folder("button") / f"{PAD}{EXT_FILE_INSTRUMENT}"
        through_the_menu = folder("menu") / f"{PAD}{EXT_FILE_INSTRUMENT}"

        def export_through_the_button(screen: Screen) -> None:
            open_voice(screen, PAD)
            screen.expect(instruments.offers_audition, bool, description="the hand-written voice open")
            screen.answer_next_dialog(DialogKind.SAVE, through_the_button)

            instruments.export(INSTRUMENT_CHANNEL)

            written(screen, through_the_button)

        def export_through_the_menu(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.SAVE, through_the_menu)

            export_from_the_menu(screen, PAD)

            written(screen, through_the_menu)
            assert through_the_menu.read_bytes() == through_the_button.read_bytes()

        screen.scenario(export_through_the_button, export_through_the_menu, leaving_asks_nothing).run()


class TestOneDialogOffersEveryType:
    """One save dialog offers the three instrument types: the type picked decides the format, and the name the
    instrument inside.
    """

    def test_the_picked_type_decides_the_format(self, screen: Screen) -> None:
        types = (FAMITRACKER_TYPE, BITPHASE_PRESET_TYPE, NSF_TYPE)
        offered: List[Tuple[str, ...]] = []

        def export_picking(screen: Screen, type_key: str, extension: str) -> Path:
            stem = folder() / PAD
            screen.answer_next_save_as(stem, screen.words(type_key))

            export_from_the_menu(screen, PAD)

            path = stem.with_suffix(extension)
            written(screen, path)
            request = screen.dialog_requests()[-1]
            assert request.title == screen.words(EXPORT_TITLE)
            assert request.suggested_name == PAD
            offered.append(tuple(file_filter.name for file_filter in request.filters))
            return path

        def the_nsf_type_writes_a_program(screen: Screen) -> None:
            path = export_picking(screen, NSF_TYPE, EXT_FILE_NSF)

            assert path.read_bytes().startswith(NSF_MAGIC)
            assert offered[0] == tuple(screen.words(key) for key in types)

        def the_bitphase_type_writes_a_preset(screen: Screen) -> None:
            path = export_picking(screen, BITPHASE_PRESET_TYPE, EXT_FILE_JSON)

            assert path.read_bytes().lstrip().startswith(JSON_OPENING)

        def the_famitracker_type_writes_an_instrument_named_after_the_file(screen: Screen) -> None:
            path = export_picking(screen, FAMITRACKER_TYPE, EXT_FILE_INSTRUMENT)

            assert path.read_bytes().startswith(FTI_MAGIC)
            assert read_fti(path).name == PAD

        def a_file_renamed_in_the_dialog_renames_the_instrument(screen: Screen) -> None:
            path = folder() / f"{RENAMED}{EXT_FILE_INSTRUMENT}"
            screen.answer_next_dialog(DialogKind.SAVE, path)

            export_from_the_menu(screen, PAD)

            written(screen, path)
            assert read_fti(path).name == RENAMED

        screen.scenario(
            the_nsf_type_writes_a_program,
            the_bitphase_type_writes_a_preset,
            the_famitracker_type_writes_an_instrument_named_after_the_file,
            a_file_renamed_in_the_dialog_renames_the_instrument,
            leaving_asks_nothing,
        ).run()
