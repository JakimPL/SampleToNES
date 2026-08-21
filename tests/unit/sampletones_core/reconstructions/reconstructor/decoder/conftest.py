from typing import Any, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.decoder.base import ChannelLattice
from sampletones_core.reconstructions.reconstructor.decoder.greedy import GreedyDecoder
from sampletones_core.reconstructions.reconstructor.decoder.viterbi import ViterbiDecoder
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate

STEADY = PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0)
JUMPED = PulseInstruction(on=True, pitch=72, volume=10, duty_cycle=0)


def state(instruction: PulseInstruction, cost: float) -> ScoredCandidate:
    return ScoredCandidate(instruction=instruction, cost=cost, approximation=None)  # type: ignore[arg-type]


def per_frame_best(frames: ChannelLattice) -> List[PulseInstruction]:
    return [min(frame, key=lambda candidate: candidate.cost).instruction for frame in frames]


@pytest.fixture
def flickering_frames() -> ChannelLattice:
    """Three frames whose per-frame best alternates, while one instruction stays cheap throughout."""
    return [
        (state(STEADY, 0.00), state(JUMPED, 0.05)),
        (state(STEADY, 0.05), state(JUMPED, 0.00)),
        (state(STEADY, 0.00), state(JUMPED, 0.05)),
    ]


@pytest.fixture
def greedy_decoder(config: Config) -> GreedyDecoder:
    return GreedyDecoder(config)


def viterbi_decoder(config: Config, **decoder_overrides: Any) -> ViterbiDecoder:
    decoder = config.generation.decoder.model_copy(update=decoder_overrides)
    updated_config = config.model_copy(update={"generation": config.generation.model_copy(update={"decoder": decoder})})
    return ViterbiDecoder(updated_config)
