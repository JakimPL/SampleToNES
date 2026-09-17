from typing import Tuple

from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID


class StemColors(BaseModel, extra="forbid", frozen=True):
    """The colors the recordings behind a reconstruction are told apart by.

    A recording takes its color from the place it holds on the record, so the ribbon under the
    waveform, the ribbon under an instrument's bars and the swatch beside a name all paint one
    recording alike. The frames a reader wrote answer to no recording and take a color of their
    own, and a resting frame shows the ground the ribbon is laid on.

    A conversion may hold more recordings than there are colors, in which case the list starts
    over, so two recordings far apart on the record can share one color while the neighbors a
    reader compares stay distinct.
    """

    recordings: Tuple[WrittenColor, ...]
    authored: WrittenColor
    rest: WrittenColor

    def for_position(self, position: int) -> WrittenColor:
        """The color the recording standing at ``position`` on the record is known by."""
        return self.recordings[position % len(self.recordings)]

    def for_stem(self, stem_id: int, position: int) -> WrittenColor:
        """The color one frame's owner is painted in.

        Args:
            stem_id: The stem holding the frame.
            position: Where that stem's entry stands on the record.

        Returns:
            WrittenColor: The color the ribbon paints that frame with.
        """
        if stem_id == RESTING_STEM_ID:
            return self.rest
        if stem_id == AUTHORED_STEM_ID:
            return self.authored

        return self.for_position(position)
