from typing import Any, Final, List, Sequence

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.decoder.base import (
    Alternatives,
    ChannelLattice,
    Lattices,
    Pool,
    PooledCombination,
    StemPools,
)
from sampletones_core.reconstructions.reconstructor.decoder.combinations import CombinationsDecoder
from sampletones_core.reconstructions.reconstructor.decoder.greedy import GreedyDecoder
from sampletones_core.reconstructions.reconstructor.decoder.viterbi import ViterbiDecoder
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate

STEADY = PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0)
JUMPED = PulseInstruction(on=True, pitch=72, volume=10, duty_cycle=0)
RAISED: Final[PulseInstruction] = PulseInstruction(on=True, pitch=STEADY.pitch + 1, volume=10, duty_cycle=0)
SEMITONE: Final[float] = 0.15


def state(instruction: PulseInstruction, cost: float) -> ScoredCandidate:
    return ScoredCandidate(instruction=instruction, cost=cost, contribution=Contribution.silence(1, 1))


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


def configured(config: Config, **decoder_overrides: Any) -> Config:
    decoder = config.generation.decoder.model_copy(update=decoder_overrides)
    return config.model_copy(update={"generation": config.generation.model_copy(update={"decoder": decoder})})


def priced_by_the_semitone(config: Config) -> Config:
    """The configuration with a decoder charging ``SEMITONE`` for each semitone a channel moves, and nothing else."""
    return configured(config, pitch_weight=SEMITONE, volume_weight=0.0, timbre_weight=0.0, on_off_weight=0.0)


def viterbi_decoder(config: Config, **decoder_overrides: Any) -> ViterbiDecoder:
    return ViterbiDecoder(configured(config, **decoder_overrides))


def combinations_decoder(config: Config, **decoder_overrides: Any) -> CombinationsDecoder:
    return CombinationsDecoder(configured(config, **decoder_overrides))


def combination(instructions: Sequence[PulseInstruction], cost: float) -> PooledCombination:
    """A whole combination of the given instructions, every channel scored at the combination's cost."""
    return PooledCombination(candidates=tuple(state(instruction, cost) for instruction in instructions), cost=cost)


def heads_pooled(lattices: Lattices) -> Alternatives:
    """The lattices with one stem holding every channel, its pool in each frame the columns' heads together."""
    channel_names = tuple(lattices)
    frames: List[Pool] = [
        (
            PooledCombination(
                candidates=tuple(lattices[name][frame][0] for name in channel_names),
                cost=max(lattices[name][frame][0].cost for name in channel_names),
            ),
        )
        for frame in range(min((len(lattice) for lattice in lattices.values()), default=0))
    ]
    return Alternatives(
        lattices=lattices,
        pools={0: StemPools(channel_names=channel_names, frames=frames)},
    )


def alone_in_a_stem(lattice: ChannelLattice) -> Alternatives:
    """One pulse's lattice, and a stem holding that pulse alone, pooling each candidate of its columns.

    A decoder of one channel at a time reads the lattice and the combinations decoder the pools, so
    both decode the same alternatives.
    """
    frames: List[Pool] = [
        tuple(PooledCombination(candidates=(candidate,), cost=candidate.cost) for candidate in column)
        for column in lattice
    ]
    return Alternatives(
        lattices={ChannelName.PULSE1: lattice},
        pools={0: StemPools(channel_names=(ChannelName.PULSE1,), frames=frames)},
    )
