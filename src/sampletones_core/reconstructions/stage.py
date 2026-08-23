from enum import StrEnum
from typing import Final, Mapping


class ReconstructionStage(StrEnum):
    """The work a reconstruction is in the middle of, as the progress it reports names it.

    A run reads its recordings onto one scale, matches every frame against the library, reads each
    channel's frames into the stream it plays, and renders that stream back to the audio the
    reconstruction carries. Each stage counts in its own unit, so what a report means is read from
    the stage it names.

    Matching visits the library once per frame per stem and is what a run spends its time on, which
    is what :data:`STAGE_SHARES` states: the bulk of the reading belongs to matching so a bar tracks
    the time a run actually takes, while the stages around it keep enough of it to move visibly as
    they pass.
    """

    LOADING = "loading"
    MATCHING = "matching"
    DECODING = "decoding"
    RENDERING = "rendering"

    @property
    def share(self) -> float:
        """How much of a whole reconstruction this stage stands for."""
        return STAGE_SHARES[self]

    @property
    def offset(self) -> float:
        """How much of a reconstruction stands finished when this stage begins."""
        offset = 0.0
        for stage in ReconstructionStage:
            if stage is self:
                break

            offset += stage.share

        return offset


STAGE_SHARES: Final[Mapping[ReconstructionStage, float]] = {
    ReconstructionStage.LOADING: 0.05,
    ReconstructionStage.MATCHING: 0.80,
    ReconstructionStage.DECODING: 0.05,
    ReconstructionStage.RENDERING: 0.10,
}
