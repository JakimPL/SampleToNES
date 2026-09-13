from pathlib import Path
from typing import Final

from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_player.nsf.information import field_size
from sampletones_player.specification.nsf import STRING_TEXT_SIZE
from tests.suite.nsf import SAMPLE_CHANNELS, project_offer, sample_offer, standing_choices

DESTINATION: Final[Path] = Path("song.nsf")
SONG_TICKS: Final[int] = 10800
NES_FREQUENCY: Final[int] = 60
LENGTH_TEMPLATE: Final[str] = "{seconds}|{ticks}|{rate}"
SIZE_TEMPLATE: Final[str] = "{used}|{room}"


def export_view(offer: NSFExportOffer, choices: NSFExportChoices) -> NSFExportViewModel:
    return NSFExportViewModel(
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

    def test_the_length_states_the_seconds_the_ticks_and_the_rate(self) -> None:
        offer = project_offer()
        view = export_view(offer, standing_choices(offer))

        seconds = SONG_TICKS / NES_FREQUENCY
        assert view.length_label(LENGTH_TEMPLATE) == f"{seconds}|{SONG_TICKS}|{NES_FREQUENCY}"

    def test_a_field_states_the_bytes_its_text_takes_against_the_room(self) -> None:
        offer = project_offer()
        view = export_view(offer, standing_choices(offer))

        label = view.text_size_label(view.choices.information.title, SIZE_TEMPLATE)

        assert label == f"{field_size(view.choices.information.title)}|{STRING_TEXT_SIZE}"
