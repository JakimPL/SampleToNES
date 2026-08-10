from dataclasses import dataclass, field
from typing import Optional

from sampletones_core.constants.general import MAX_VOLUME

from ..protocol import ChannelGeneratorProtocol


@dataclass
class ChannelState:
    """What one channel carries from row to row.

    A pattern states a channel's instrument, transpose, and volume only where it changes them, so
    the channel keeps the last of each until another row states otherwise. The tick index is how
    far into the sounding sample's instructions the channel has played, which is what lets a note
    sustain across rows.

    Attributes:
        generator: The synthesiser filling the channel's ticks.
        sample_id: The sample the channel is sounding, or ``None`` while it is silent.
        tick_index: How many ticks of that sample's instructions the channel has played.
        transpose: The semitone offset a row last set.
        volume: The level a row last set.
    """

    generator: ChannelGeneratorProtocol
    sample_id: Optional[str] = field(default=None)
    tick_index: int = field(default=0)
    transpose: int = field(default=0)
    volume: int = field(default=MAX_VOLUME)

    def reset(self) -> None:
        """Returns the channel to silence at full volume, as a song starts it.

        The generator is kept, since it is built from the rates in force rather than from
        anything a song reaches.
        """
        self.sample_id = None
        self.tick_index = 0
        self.transpose = 0
        self.volume = MAX_VOLUME
