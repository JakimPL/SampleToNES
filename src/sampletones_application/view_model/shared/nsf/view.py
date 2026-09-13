from pathlib import Path
from typing import Tuple

from pydantic import BaseModel

from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_core.constants.enums import ChannelName
from sampletones_core.parallelization import ETAEstimator
from sampletones_player.compression.scheme import CompressionScheme


class NSFExportViewModel(BaseModel, frozen=True):
    """What the NSF export dialog draws: what the source offers, the choices standing, and the file.

    The dialog stands while an export is set up, and the run that follows reports through the
    export's own window, so everything here describes the setup.

    Attributes:
        offer: What the source leaves to choose.
        choices: The choices the dialog is standing at.
        destination: The file the export writes.
        ticks: The ticks the song lasts with the ticked channels sounding.
        nes_frequency: The rate in Hz the console plays those ticks at.
    """

    offer: NSFExportOffer
    choices: NSFExportChoices
    destination: Path
    ticks: int
    nes_frequency: int

    @property
    def channels(self) -> Tuple[ChannelName, ...]:
        return self.offer.channels

    @property
    def repeats(self) -> Tuple[NSFRepeat, ...]:
        return self.offer.repeats

    @property
    def schemes(self) -> Tuple[CompressionScheme, ...]:
        return self.offer.schemes

    @property
    def last_frame(self) -> int:
        return self.offer.last_frame

    @property
    def loop_frame_visible(self) -> bool:
        """Whether a frame is chosen here, which a repeat returning to one is what asks for."""
        return self.choices.repeat == NSFRepeat.FROM_FRAME

    @property
    def export_enabled(self) -> bool:
        """Whether the program is written from here: at least one channel sounds in it."""
        return self.choices.writable

    @property
    def duration_seconds(self) -> float:
        """How long the song plays for, in seconds."""
        return self.ticks / self.nes_frequency

    def channel_offered(self, channel: ChannelName) -> bool:
        """Whether ``channel`` takes a tick, which the source sounding it is what decides."""
        return channel in self.offer.channels

    def channel_sounded(self, channel: ChannelName) -> bool:
        """Whether the program sounds ``channel``."""
        return channel in self.choices.channels

    def length_label(self, template: str) -> str:
        """How long the song plays for and the ticks it takes, as ``template`` states them."""
        return template.format(
            duration=ETAEstimator.format_duration(self.duration_seconds),
            ticks=self.ticks,
            rate=self.nes_frequency,
        )

    def frame_count_label(self, template: str) -> str:
        """The frames the song is laid out in, as ``template`` states them."""
        return template.format(count=self.offer.frame_count)
