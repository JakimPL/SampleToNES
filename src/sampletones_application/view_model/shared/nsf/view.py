from pathlib import Path
from typing import Tuple

from pydantic import BaseModel

from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.nsf.information import field_size
from sampletones_player.specification.nsf import STRING_TEXT_SIZE
from sampletones_shared.utils.time import format_span


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
        """How long the song plays for, as a span and in ticks, as ``template`` states it."""
        return template.format(
            length=format_span(self.duration_seconds),
            ticks=self.ticks,
            rate=self.nes_frequency,
        )

    def text_size_label(self, text: str, template: str) -> str:
        """The bytes ``text`` takes in its header field against the room there, as ``template`` states them."""
        return template.format(used=field_size(text), room=STRING_TEXT_SIZE)

    def loop_frame_label(self, template: str) -> str:
        """The order frame a repeat returns to, as ``template`` states it."""
        return template.format(frame=self.choices.loop_frame)

    def frame_count_label(self, template: str) -> str:
        """The frames the song is laid out in, as ``template`` states them."""
        return template.format(count=self.offer.frame_count)
