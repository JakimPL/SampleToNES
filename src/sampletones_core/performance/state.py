from dataclasses import dataclass, field
from typing import Dict, Optional

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS


@dataclass
class ChannelPerformance:
    """What one channel carries from row to row while a song plays.

    A pattern states a channel's voice, transpose, and volume only where it changes them, so the
    channel keeps the last of each until another row states otherwise. The tick index is how far
    into the sounding voice's instructions the channel has played, which is what lets a note
    sustain across rows.

    The channel carries a value per envelope dimension too, which is what an instrument leaving a
    dimension to the channel sounds at. Every note starts them from the values a song starts on,
    and a frame the instrument writes hands its value over, so the channel keeps the last one
    written for as long as the note sounds.

    Attributes:
        voice_id: The voice the channel is sounding, or ``None`` while it is silent.
        tick_index: How many ticks of that voice's instructions the channel has played.
        transpose: The semitone offset a row last set.
        volume: The level a row last set.
        feature_values: The value the channel holds for each envelope dimension.
    """

    voice_id: Optional[str] = field(default=None)
    tick_index: int = field(default=0)
    transpose: int = field(default=0)
    volume: int = field(default=MAX_VOLUME)
    feature_values: Dict[FeatureKey, int] = field(default_factory=CHANNEL_FEATURE_DEFAULTS.copy)

    def start_note(
        self,
        voice_id: str,
        *,
        transpose: int,
        volume: int,
    ) -> None:
        """Begins a note of ``voice_id`` from its first tick, at the transpose and volume given.

        The envelope dimensions start from the values a song starts on: full volume, no arpeggio
        offset, no bend and the first timbre. A dimension the voice leaves empty therefore sounds
        the same on every note, wherever the note stands in the song, which is how FamiTracker and
        Bitphase start a note and what keeps a tracker export playing it as the song does.

        Args:
            voice_id: The voice the note sounds.
            transpose: The semitone offset the note plays at.
            volume: The level the note plays at.
        """
        self.voice_id = voice_id
        self.tick_index = 0
        self.transpose = transpose
        self.volume = volume
        self.feature_values = CHANNEL_FEATURE_DEFAULTS.copy()

    def reset(self) -> None:
        """Returns the channel to silence at full volume, as a song starts it.

        The envelope dimensions return to the values a channel holds from the start of a song,
        so a pass through the song sounds the same however the previous one left them.
        """
        self.voice_id = None
        self.tick_index = 0
        self.transpose = 0
        self.volume = MAX_VOLUME
        self.feature_values = CHANNEL_FEATURE_DEFAULTS.copy()
