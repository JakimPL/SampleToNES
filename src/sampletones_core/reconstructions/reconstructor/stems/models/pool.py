from typing import NamedTuple, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.decoder.base import Pool


class StemPool(NamedTuple):
    """One stem's whole combinations in one frame, which a decoder over combinations chooses among.

    Attributes:
        stem_id: The stem.
        channel_names: The stem's channels, in the order every combination lists them.
        combinations: The combinations, each scored at the full cost of the stem's frame.
    """

    stem_id: int
    channel_names: Tuple[ChannelName, ...]
    combinations: Pool
