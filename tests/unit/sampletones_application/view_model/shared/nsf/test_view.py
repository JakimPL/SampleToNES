from pathlib import Path
from typing import Final

from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.parallelization import ETAEstimator
from tests.suite.nsf import SAMPLE_CHANNELS, project_offer, sample_offer, standing_choices

DESTINATION: Final[Path] = Path("song.nsf")
SONG_TICKS: Final[int] = 10800
NES_FREQUENCY: Final[int] = 60
LENGTH_TEMPLATE: Final[str] = "{duration}|{ticks}|{rate}"


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

    def test_the_length_states_the_duration_the_ticks_and_the_rate(self) -> None:
        offer = project_offer()
        view = export_view(offer, standing_choices(offer))

        duration = ETAEstimator.format_duration(SONG_TICKS / NES_FREQUENCY)
        assert view.length_label(LENGTH_TEMPLATE) == f"{duration}|{SONG_TICKS}|{NES_FREQUENCY}"
