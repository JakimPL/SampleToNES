from enum import StrEnum
from typing import Final, Mapping


class ReconstructionStage(StrEnum):
    """The work a reconstruction is in the middle of, as the progress it reports names it.

    A run reads its recordings onto one scale, matches every frame against the library, reads each
    channel's frames into the stream it plays, and gathers those streams into the document it
    answers with. Each stage counts in its own unit, so what a report means is read from the stage
    it names.

    Matching visits the library once per frame per stem and is the whole of what a run spends its
    time on: measured over whole runs it takes some ninety-seven parts in a hundred, decoding two,
    and the gathering a tenth of one. :data:`STAGE_WEIGHTS` turns those measurements into shares a
    bar reads well. Loading takes eight, because a run opening a library of its own pays that
    reading once and a short recording spends a quarter of itself on it — a bar standing still is
    noticed, while one moving a little early is not. The gathering takes one so the last stage
    moves visibly, decoding keeps the two it measures, and matching keeps the eighty-nine that
    remain.

    The weights are counts, each stating what a stage is worth against the others, and a reading
    divides once at the point of use — which is what lets the last stage arrive exactly at the
    whole run.
    """

    LOADING = "loading"
    MATCHING = "matching"
    DECODING = "decoding"
    GATHERING = "gathering"

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
    ReconstructionStage.MATCHING: 89,
    ReconstructionStage.DECODING: 2,
    ReconstructionStage.GATHERING: 1,
}

TOTAL_STAGE_WEIGHT: Final[int] = sum(STAGE_WEIGHTS.values())
