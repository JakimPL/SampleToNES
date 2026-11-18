from pathlib import Path
from typing import Final

from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.format import ExportFormat
from sampletones_player.nsf.header import HEADER_LINE, HEADER_TEXT
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from sampletones_shared.utils.time import format_span
from tests.suite.nsf import (
    NARROW_TEXT,
    OTHER_EXTENSION,
    OTHER_FORMAT,
    SAMPLE_CHANNELS,
    project_offer,
    sample_offer,
    standing_choices,
)

DESTINATION: Final[Path] = Path("song.nsf")
SONG_TICKS: Final[int] = 10800
NES_FREQUENCY: Final[int] = 60
LENGTH_TEMPLATE: Final[str] = "{length}|{ticks}|{rate}"
SIZE_TEMPLATE: Final[str] = "{used}|{room}"
WIDE_TEXT: Final[str] = "Zażółć"


def export_view(offer: NSFExportOffer, choices: NSFExportChoices) -> NSFExportViewModel:
    return NSFExportViewModel(
        export_format=ExportFormat.NSF,
        extension=EXT_FILE_NSF,
        text=HEADER_TEXT,
        offer=offer,
        choices=choices,
        destination=DESTINATION,
        ticks=SONG_TICKS,
        nes_frequency=NES_FREQUENCY,
    )


class TestTheSetupShowsTheChoices:
    def test_the_frame_is_asked_for_once_the_repeat_returns_to_one(self) -> None:
        offer = project_offer()
        choices = standing_choices(offer)

        assert not export_view(offer, choices).loop_frame_visible
        assert export_view(offer, choices.with_repeat(NSFRepeat.FROM_FRAME, offer)).loop_frame_visible

    def test_the_program_is_written_while_a_channel_sounds(self) -> None:
        offer = sample_offer()
        choices = standing_choices(offer)
        silent = choices
        for channel in SAMPLE_CHANNELS:
            silent = silent.with_channel(channel, False, offer)

        assert export_view(offer, choices).export_enabled
        assert not export_view(offer, silent).export_enabled

    def test_a_channel_takes_a_tick_where_the_source_sounds_it(self) -> None:
        offer = sample_offer()
        view = export_view(offer, standing_choices(offer))

        assert view.channel_offered(ChannelName.TRIANGLE)
        assert not view.channel_offered(ChannelName.NOISE)

    def test_the_length_states_the_span_the_ticks_and_the_rate(self) -> None:
        offer = project_offer()
        view = export_view(offer, standing_choices(offer))

        span = format_span(SONG_TICKS / NES_FREQUENCY)
        assert view.length_label(LENGTH_TEMPLATE) == f"{span}|{SONG_TICKS}|{NES_FREQUENCY}"

    def test_a_field_states_the_bytes_its_text_takes_against_the_room(self) -> None:
        offer = project_offer()
        view = export_view(offer, standing_choices(offer))

        label = view.text_size_label(view.choices.information.title, view.text.title, SIZE_TEMPLATE)

        assert label == f"{HEADER_LINE.size(view.choices.information.title)}|{HEADER_LINE.room}"

    def test_the_room_a_field_states_is_the_one_its_line_has(self) -> None:
        offer = project_offer()
        view = NSFExportViewModel(
            export_format=OTHER_FORMAT,
            extension=OTHER_EXTENSION,
            text=NARROW_TEXT,
            offer=offer,
            choices=standing_choices(offer),
            destination=DESTINATION,
            ticks=SONG_TICKS,
            nes_frequency=NES_FREQUENCY,
        )

        label = view.text_size_label(WIDE_TEXT, view.text.artist, SIZE_TEMPLATE)

        assert label == f"{NARROW_TEXT.artist.size(WIDE_TEXT)}|{NARROW_TEXT.artist.room}"
