from dataclasses import dataclass, field
from typing import Dict, Optional

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS


@dataclass
class ChannelPerformance:
    """What one channel carries from row to row while a song plays.

    A pattern states a channel's instrument, transpose, and volume only where it changes them, so
    the channel keeps the last of each until another row states otherwise. The tick index is how
    far into the sounding sample's instructions the channel has played, which is what lets a note
    sustain across rows.

    The channel carries a value per envelope dimension too, which is what an instrument leaving a
    dimension to the channel sounds at. A frame the instrument writes hands its value over, so the
    channel keeps the last one written for as long as the song runs.

    Attributes:
        sample_id: The sample the channel is sounding, or ``None`` while it is silent.
        tick_index: How many ticks of that sample's instructions the channel has played.
        transpose: The semitone offset a row last set.
        volume: The level a row last set.
        feature_values: The value the channel holds for each envelope dimension.
    """

    sample_id: Optional[str] = field(default=None)
    tick_index: int = field(default=0)
    transpose: int = field(default=0)
    volume: int = field(default=MAX_VOLUME)
    feature_values: Dict[FeatureKey, int] = field(default_factory=CHANNEL_FEATURE_DEFAULTS.copy)

    def reset(self) -> None:
        """Returns the channel to silence at full volume, as a song starts it.

        The envelope dimensions return to the values a channel holds from the start of a song,
        so a pass through the song sounds the same however the previous one left them.
        """
        self.sample_id = None
        self.tick_index = 0
        self.transpose = 0
        self.volume = MAX_VOLUME
        self.feature_values = CHANNEL_FEATURE_DEFAULTS.copy()
