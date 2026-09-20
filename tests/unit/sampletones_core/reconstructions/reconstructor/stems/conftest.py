from typing import Dict, Final, List, Mapping, Sequence

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import SINGLE_STATE_LATTICE_WIDTH, UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher, ScoredCandidate
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker

RENDERED_FRAMES: Final[int] = 5


@pytest.fixture(scope="module")
def matcher(worker: ReconstructorWorker) -> FrameMatcher:
    return worker.matcher


@pytest.fixture(scope="module")
def all_channels(config: Config) -> Dict[ChannelName, GeneratorUnion]:
    return get_generators_by_channels(config, ChannelName.items())


def rendered_fragment(
    config: Config,
    extractor: FeatureExtractor,
    instructions: Mapping[ChannelName, InstructionUnion],
) -> Fragment:
    """A frame of the channels playing ``instructions`` together, taken from the middle of a held note."""
    audio = sum(
        (
            render_instructions([instruction] * RENDERED_FRAMES, channel_name, config)
            for channel_name, instruction in instructions.items()
        ),
        start=np.zeros(RENDERED_FRAMES * config.library.frame_length, dtype=np.float32),
    )
    return extractor.extract(audio)[RENDERED_FRAMES // 2]


def audible_instruction_of(library_data: InstructionLibraryData, generator: GeneratorUnion) -> InstructionUnion:
    """The first sounding instruction the library holds for ``generator``'s class."""
    return next(instruction for instruction in library_data.filter((generator.class_name(),)).keys() if instruction.on)


def frame_objective_baseline(
    fragment: Fragment,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    drive: float = UNIT_DRIVE,
) -> Dict[ChannelName, ScoredCandidate]:
    """The frame objective restated one candidate at a time, as the assignment's reference.

    Every candidate of every free channel's kind is scored alone at ``drive`` by the frame's cost
    with the picks so far sounding beside it, the lowest free channel of a kind standing for the
    kind. The pick lowering the frame's cost the most is taken while one exists; the channels no
    pick lowers hold their silence; every channel is then scored once more with the others' heads
    sounding. A one-stem setup at full count driving every channel alike runs exactly this, which
    is what makes the two comparable frame by frame.
    """
    heads: Dict[ChannelName, ScoredCandidate] = {}
    frame_cost = matcher.mix_cost(fragment, FrameMix.empty(fragment))
    while True:
        best = None
        for channel_name in _representatives(channels, heads):
            context = [head.contribution for head in heads.values()]
            head = _column(fragment, channels[channel_name], context, matcher, drive)[0]
            if head.instruction.on and head.cost < frame_cost and (best is None or head.cost < best[1].cost):
                best = (channel_name, head)

        if best is None:
            break

        heads[best[0]] = best[1]
        frame_cost = best[1].cost

    for channel_name in channels:
        if channel_name not in heads:
            sounding = [head.contribution for head in heads.values() if head.instruction.on]
            heads[channel_name] = _column(fragment, channels[channel_name], sounding, matcher, drive)[0]

    for channel_name in list(heads):
        others = [head.contribution for name, head in heads.items() if name != channel_name and head.instruction.on]
        heads[channel_name] = _column(fragment, channels[channel_name], others, matcher, drive)[0]

    return heads


def _representatives(
    channels: Dict[ChannelName, GeneratorUnion],
    taken: Mapping[ChannelName, ScoredCandidate],
) -> List[ChannelName]:
    representatives: Dict[GeneratorClassName, ChannelName] = {}
    for channel_name, generator in channels.items():
        if channel_name not in taken:
            representatives.setdefault(generator.class_name(), channel_name)

    return list(representatives.values())


def _column(
    fragment: Fragment,
    generator: GeneratorUnion,
    context: Sequence[Contribution],
    matcher: FrameMatcher,
    drive: float,
) -> List[ScoredCandidate]:
    library_data = matcher.candidate_provider.library_data
    scored = [
        _scored_alone(fragment, context, instruction, matcher, drive)
        for instruction in library_data.filter((generator.class_name(),)).keys()
    ]
    return sorted(scored, key=lambda candidate: (candidate.cost, candidate.instruction.on))


def _scored_alone(
    fragment: Fragment,
    context: Sequence[Contribution],
    instruction: InstructionUnion,
    matcher: FrameMatcher,
    drive: float,
) -> ScoredCandidate:
    provider = matcher.candidate_provider
    mix = FrameMix.of(fragment, context)
    power = provider.power_of(instruction) / drive**2
    contribution = matcher.contribution(instruction, mix.residual_waveform(fragment), power, drive=drive)
    spectral = matcher.scorer.spectral_costs(fragment, provider.features_of((mix.power + power)[None, :]))
    cost = matcher.scorer.frame_costs(
        fragment,
        spectral,
        (mix.expectation + contribution.expectation)[None, :],
        np.array([mix.variance + contribution.variance]),
    )[0]
    return ScoredCandidate(instruction=instruction, cost=float(cost), contribution=contribution)


@pytest.fixture(scope="module")
def lattice_width() -> int:
    """The width a greedy decoder reads, which is what the equivalence baseline assumes."""
    return SINGLE_STATE_LATTICE_WIDTH


def shared_frames(fragment: Fragment, stems_config: StemsConfig) -> Dict[int, Fragment]:
    """The frame every stem of ``stems_config`` contributes, one entry apiece.

    Stems sounding alike leave hierarchy order, the channel cap and tie resolution as the only
    things deciding the frame, which is what a case using this states.
    """
    return {entry.id: fragment for entry in stems_config.entries}
