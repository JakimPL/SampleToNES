from __future__ import annotations

from typing import FrozenSet, Optional

from pydantic import BaseModel

from sampletones_application.view_model.shared.nsf.offer import FIRST_FRAME, NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_core.constants.enums import ChannelName
from sampletones_player.builder import SONG_START
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.export.program import NSFProgram
from sampletones_player.nsf.information import NSFInformation


class NSFExportChoices(BaseModel, frozen=True):
    """The choices a program is written under, as the export dialog edits them.

    The player owns what a program may state, so the text is held as the header fields it becomes,
    cut to the room each has, and every ``with_`` method reconciles its edit against what the source
    offers: a channel the source leaves silent stays unticked, a repeat returns to a frame the song
    has, and a scheme is one that writes the source differently. Every value held here is therefore
    one the program is written with.

    Attributes:
        information: The text the file is listed under.
        channels: The channels ticked for the program to sound.
        repeat: Where the program goes once its song ends.
        loop_frame: The order frame a repeat from a frame returns to.
        scheme: The layers of the codec the song is written with.
    """

    information: NSFInformation
    channels: FrozenSet[ChannelName]
    repeat: NSFRepeat
    loop_frame: int
    scheme: CompressionScheme

    @classmethod
    def initial(cls, program: NSFProgram, offer: NSFExportOffer) -> NSFExportChoices:
        """The choices a dialog opens on: the program an export writes as its source states it.

        Args:
            program: The program the source states.
            offer: What the source leaves to choose.

        Returns:
            NSFExportChoices: The stated program, its channels narrowed to the ones the source sounds.

        Raises:
            ValueError: If the program repeats from a tick past the song's start.
        """
        return cls(
            information=program.information,
            channels=program.channels.intersection(offer.channels),
            repeat=cls._stated_repeat(program.loop_tick),
            loop_frame=FIRST_FRAME,
            scheme=program.scheme,
        )

    @property
    def writable(self) -> bool:
        """Whether a program is written under these choices, which a ticked channel is what makes."""
        return bool(self.channels)

    def with_title(self, title: str) -> NSFExportChoices:
        """The choices listing the file under ``title``, as much of it as the field holds."""
        return self._with_information(
            NSFInformation(
                title=title,
                artist=self.information.artist,
                copyright=self.information.copyright,
            )
        )

    def with_artist(self, artist: str) -> NSFExportChoices:
        """The choices crediting the file to ``artist``, as much of it as the field holds."""
        return self._with_information(
            NSFInformation(
                title=self.information.title,
                artist=artist,
                copyright=self.information.copyright,
            )
        )

    def with_copyright(self, copyright_text: str) -> NSFExportChoices:
        """The choices stating ``copyright_text`` as the rights, as much of it as the field holds."""
        return self._with_information(
            NSFInformation(
                title=self.information.title,
                artist=self.information.artist,
                copyright=copyright_text,
            )
        )

    def with_channel(
        self,
        channel: ChannelName,
        sounded: bool,
        offer: NSFExportOffer,
    ) -> NSFExportChoices:
        """The choices sounding ``channel`` or resting it, among the channels the source sounds.

        Args:
            channel: The channel ticked or unticked.
            sounded: Whether the program sounds it.
            offer: What the source leaves to choose.

        Returns:
            NSFExportChoices: The choices with the channel ticked as asked where the source sounds
            it, and the choices as they stand otherwise.
        """
        if channel not in offer.channels:
            return self

        channels = self.channels | {channel} if sounded else self.channels - {channel}
        return self.model_copy(update={"channels": channels})

    def with_repeat(self, repeat: NSFRepeat, offer: NSFExportOffer) -> NSFExportChoices:
        """The choices going on as ``repeat`` states, where the source offers it.

        Returns:
            NSFExportChoices: The choices with the repeat as asked where the source offers it, and
            the choices as they stand otherwise.
        """
        if repeat not in offer.repeats:
            return self

        return self.model_copy(update={"repeat": repeat})

    def with_loop_frame(self, frame: int, offer: NSFExportOffer) -> NSFExportChoices:
        """The choices returning to ``frame``, brought within the frames the song is laid out in."""
        return self.model_copy(update={"loop_frame": min(max(frame, FIRST_FRAME), offer.last_frame)})

    def with_scheme(self, scheme: CompressionScheme, offer: NSFExportOffer) -> NSFExportChoices:
        """The choices writing the song under ``scheme``, where the source offers it.

        Returns:
            NSFExportChoices: The choices with the scheme as asked where the source offers it, and
            the choices as they stand otherwise.
        """
        if scheme not in offer.schemes:
            return self

        return self.model_copy(update={"scheme": scheme})

    def _with_information(self, information: NSFInformation) -> NSFExportChoices:
        return self.model_copy(update={"information": information})

    @staticmethod
    def _stated_repeat(loop_tick: Optional[int]) -> NSFRepeat:
        """The repeat a stated program's loop reads as: once without one, and from the start with one.

        Raises:
            ValueError: If the loop returns to a tick past the song's start.
        """
        match loop_tick:
            case None:
                return NSFRepeat.ONCE
            case tick if tick == SONG_START:
                return NSFRepeat.FROM_START
            case tick:
                raise ValueError(f"A stated program repeats from the song's start, and this one repeats from {tick}")
