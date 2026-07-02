from __future__ import annotations

from typing import Any, Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import Window
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.selector.viterbi import (
    CandidateState,
    ViterbiSelector,
)
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


def _selector(
    config: Config,
    window: Window,
    generators: Dict[GeneratorName, GeneratorUnion],
    worker: ReconstructorWorker,
    **decoder_overrides: Any,
) -> ViterbiSelector:
    decoder = config.generation.decoder.model_copy(update=decoder_overrides)
    updated_config = config.model_copy(update={"generation": config.generation.model_copy(update={"decoder": decoder})})
    return ViterbiSelector(
        updated_config,
        window,
        generators,
        worker.scorer,
        worker.candidate_provider,
        worker.phase_aligner,
        worker.feature_extractor,
    )


def _state(instruction: PulseInstruction, emission: float) -> CandidateState:
    return CandidateState(instruction=instruction, emission=emission, approximation=None)  # type: ignore[arg-type]


def _per_frame_best(frames: List[List[CandidateState]]) -> List[PulseInstruction]:
    return [min(frame, key=lambda state: state.emission).instruction for frame in frames]


STEADY = PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0)
JUMPED = PulseInstruction(on=True, pitch=72, volume=10, duty_cycle=0)


def _flickering_frames() -> List[List[CandidateState]]:
    return [
        [_state(STEADY, 0.00), _state(JUMPED, 0.05)],
        [_state(STEADY, 0.05), _state(JUMPED, 0.00)],
        [_state(STEADY, 0.00), _state(JUMPED, 0.05)],
    ]


class TestViterbiContinuity:
    def test_continuity_holds_a_steady_note_where_per_frame_choice_flickers(
        self,
        config: Config,
        window: Window,
        generators: Dict[GeneratorName, GeneratorUnion],
        worker: ReconstructorWorker,
    ) -> None:
        selector = _selector(config, window, generators, worker, pitch_weight=1.0)
        frames = _flickering_frames()

        path = selector._decode(frames)
        chosen = [frames[position][path[position]].instruction for position in range(len(frames))]

        assert len({id(instruction) for instruction in _per_frame_best(frames)}) > 1
        assert len(set(chosen)) == 1

    def test_zero_transition_weights_reduce_to_per_frame_choice(
        self,
        config: Config,
        window: Window,
        generators: Dict[GeneratorName, GeneratorUnion],
        worker: ReconstructorWorker,
    ) -> None:
        selector = _selector(
            config,
            window,
            generators,
            worker,
            pitch_weight=0.0,
            volume_weight=0.0,
            timbre_weight=0.0,
            on_off_weight=0.0,
        )
        frames = _flickering_frames()

        path = selector._decode(frames)
        chosen = [frames[position][path[position]].instruction for position in range(len(frames))]

        assert chosen == _per_frame_best(frames)


class TestViterbiTransitionCost:
    def test_identical_instruction_has_no_cost(
        self,
        config: Config,
        window: Window,
        generators: Dict[GeneratorName, GeneratorUnion],
        worker: ReconstructorWorker,
    ) -> None:
        selector = _selector(config, window, generators, worker)
        assert selector._transition_cost(STEADY, STEADY) == 0.0

    def test_larger_pitch_jump_costs_more(
        self,
        config: Config,
        window: Window,
        generators: Dict[GeneratorName, GeneratorUnion],
        worker: ReconstructorWorker,
    ) -> None:
        selector = _selector(config, window, generators, worker, pitch_weight=0.1)
        near = PulseInstruction(on=True, pitch=61, volume=10, duty_cycle=0)
        far = PulseInstruction(on=True, pitch=84, volume=10, duty_cycle=0)
        assert selector._transition_cost(STEADY, near) < selector._transition_cost(STEADY, far)

    def test_toggling_on_off_costs_the_on_off_weight(
        self,
        config: Config,
        window: Window,
        generators: Dict[GeneratorName, GeneratorUnion],
        worker: ReconstructorWorker,
    ) -> None:
        selector = _selector(config, window, generators, worker, on_off_weight=0.25)
        silence = PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=0)
        assert selector._transition_cost(STEADY, silence) == 0.25


class TestViterbiSelectIntegration:
    def test_select_is_deterministic(
        self,
        worker: ReconstructorWorker,
        fragmented_audio: Any,
    ) -> None:
        fragment_ids = fragmented_audio.fragments_ids
        first = worker(fragmented_audio, fragment_ids)
        second = worker(fragmented_audio, fragment_ids)
        for fragment_id in fragment_ids:
            for generator_name in first[fragment_id]:
                assert first[fragment_id][generator_name].instruction == second[fragment_id][generator_name].instruction
