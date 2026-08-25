from enum import StrEnum
from typing import Final, Mapping


class ReconstructionStage(StrEnum):
    """The work a reconstruction is in the middle of, as the progress it reports names it.

    A run reads its recordings onto one scale, matches every frame against the library, reads each
    channel's frames into the stream it plays, and renders that stream back to the audio the
    reconstruction carries. Each stage counts in its own unit, so what a report means is read from
    the stage it names.

    Matching visits the library once per frame per stem and is what a run spends its time on, which
    is what :data:`STAGE_WEIGHTS` states: the bulk of a reading belongs to matching so a bar tracks
    the time a run actually takes, while the stages around it keep enough of it to move visibly as
    they pass. The weights are approximations measured over whole runs, and matching earns a larger
    share the longer the recording is, so the stages around it are given what they hold on a short
    one — where a bar standing still is noticed.

    The weights are counts rather than fractions, so what a stage is worth is stated against the
    others and a reading is one division at the point of use — which is what lets the last stage
    arrive exactly at the whole run.
    """

    LOADING = "loading"
    MATCHING = "matching"
    DECODING = "decoding"
    RENDERING = "rendering"

    @property
    def weight(self) -> int:
        """What this stage costs, against the other stages of a run."""
        return STAGE_WEIGHTS[self]

    @property
    def preceding_weight(self) -> int:
        """What the stages before this one cost together."""
        preceding = 0
        for stage in ReconstructionStage:
            if stage is self:
                break

            preceding += stage.weight

        return preceding

    @property
    def share(self) -> float:
        """How much of a whole reconstruction this stage stands for."""
        return self.weight / TOTAL_STAGE_WEIGHT

    @property
    def offset(self) -> float:
        """How much of a reconstruction stands finished when this stage begins."""
        return self.preceding_weight / TOTAL_STAGE_WEIGHT


STAGE_WEIGHTS: Final[Mapping[ReconstructionStage, int]] = {
    ReconstructionStage.LOADING: 8,
    ReconstructionStage.MATCHING: 82,
    ReconstructionStage.DECODING: 2,
    ReconstructionStage.RENDERING: 8,
}

TOTAL_STAGE_WEIGHT: Final[int] = sum(STAGE_WEIGHTS.values())
