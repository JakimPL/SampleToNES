from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import Fragment, Window
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import PulseInstruction
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.reconstructor import reconstruct
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


class TestReconstructorWorkerHelpers:
    def test_get_remaining_generators_returns_all_generators(
        self,
        worker: ReconstructorWorker,
        generators: Dict[GeneratorName, GeneratorUnion],
    ) -> None:
        remaining = worker.get_remaining_generators()
        assert set(remaining.keys()) == set(generators.keys())

    def test_get_remaining_generators_returns_independent_copy(
        self,
        worker: ReconstructorWorker,
    ) -> None:
        remaining = worker.get_remaining_generators()
        key = next(iter(remaining))
        del remaining[key]
        assert key in worker.generators

    def test_get_remaining_generator_classes_maps_by_class_name(
        self,
        worker: ReconstructorWorker,
        generators: Dict[GeneratorName, GeneratorUnion],
    ) -> None:
        remaining = worker.get_remaining_generators()
        by_class = worker.get_remaining_generator_classes(remaining)
        expected_class_names = {gen.class_name() for gen in generators.values()}
        assert set(by_class.keys()) == expected_class_names

    def test_serialize_instructions_is_deterministic(self) -> None:
        instructions = (
            PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0),
            PulseInstruction(on=True, pitch=72, volume=15, duty_cycle=1),
        )
        first = ReconstructorWorker._serialize_instructions(instructions)
        second = ReconstructorWorker._serialize_instructions(instructions)
        assert first == second

    def test_serialize_instructions_differs_for_different_instructions(self) -> None:
        instructions_a = (PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0),)
        instructions_b = (PulseInstruction(on=True, pitch=72, volume=15, duty_cycle=1),)
        assert ReconstructorWorker._serialize_instructions(
            instructions_a
        ) != ReconstructorWorker._serialize_instructions(instructions_b)


class TestReconstructorWorkerIntegration:
    def test_call_returns_dict_keyed_by_fragment_id(
        self,
        worker: ReconstructorWorker,
        fragmented_audio: Any,
    ) -> None:
        fragment_ids = fragmented_audio.fragments_ids
        result = worker(fragmented_audio, fragment_ids)
        assert set(result.keys()) == set(fragment_ids)

    def test_call_result_has_one_entry_per_generator(
        self,
        worker: ReconstructorWorker,
        fragmented_audio: Any,
        generators: Dict[GeneratorName, GeneratorUnion],
    ) -> None:
        result = worker(fragmented_audio, [fragmented_audio.fragments_ids[0]])
        per_fragment = next(iter(result.values()))
        assert set(per_fragment.keys()) == set(generators.keys())

    def test_approximation_data_has_valid_generator_name(
        self,
        worker: ReconstructorWorker,
        generators: Dict[GeneratorName, GeneratorUnion],
        synthetic_fragment: Fragment,
    ) -> None:
        result = worker.reconstruct(synthetic_fragment)
        for generator_name in result:
            assert generator_name in generators

    def test_combined_approximation_is_not_all_zeros(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        result = worker.reconstruct(synthetic_fragment)
        combined = sum(np.asarray(approx_data.approximation.audio) for approx_data in result.values())
        assert not np.all(combined == 0.0)

    def test_reconstruction_reduces_residual(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        original_audio = np.asarray(synthetic_fragment.audio).copy()
        result = worker.reconstruct(synthetic_fragment)
        residual_audio = original_audio.copy()
        for approximation_data in result.values():
            residual_audio = residual_audio - np.asarray(approximation_data.approximation.audio)
        original_rmse = float(np.sqrt(np.mean(original_audio**2)))
        residual_rmse = float(np.sqrt(np.mean(residual_audio**2)))
        assert residual_rmse < original_rmse

    def test_without_find_best_phase_produces_valid_approximation(
        self,
        config: Config,
        window: Window,
        generators: Dict[GeneratorName, GeneratorUnion],
        library_data: InstructionLibraryData,
    ) -> None:
        updated_config = config.model_copy(
            update={
                "generation": config.generation.model_copy(
                    update={
                        "calculation": config.generation.calculation.model_copy(
                            update={
                                "find_best_phase": False,
                            }
                        )
                    }
                )
            }
        )
        active_instruction = next(instrument for instrument in library_data.keys() if instrument.on)
        fragment = library_data[active_instruction].get_fragment(0, updated_config, window)
        local_worker = ReconstructorWorker(
            config=updated_config,
            window=window,
            generators=generators,
            library_data=library_data,
            signal_length=1 << 20,
        )
        result = local_worker.reconstruct(fragment)
        combined = sum(np.asarray(approximation_data.approximation.audio) for approximation_data in result.values())
        assert not np.all(combined == 0.0)


class TestModuleLevelReconstruct:
    def _call(
        self,
        worker: ReconstructorWorker,
        fragmented_audio: Any,
        library_data: InstructionLibraryData,
        fragment_ids: List[int],
    ) -> Any:
        return reconstruct(
            fragments_ids=fragment_ids,
            fragmented_audio=fragmented_audio,
            config=worker.config,
            window=worker.window,
            generators=worker.generators,
            library_data=library_data,
        )

    def test_returns_dict_keyed_by_fragment_id(
        self,
        worker: ReconstructorWorker,
        fragmented_audio: Any,
        library_data: InstructionLibraryData,
    ) -> None:
        fragment_ids = [fragmented_audio.fragments_ids[0]]
        result = self._call(worker, fragmented_audio, library_data, fragment_ids)
        assert set(result.keys()) == set(fragment_ids)

    def test_covers_all_requested_fragment_ids(
        self,
        worker: ReconstructorWorker,
        fragmented_audio: Any,
        library_data: InstructionLibraryData,
    ) -> None:
        fragment_ids = fragmented_audio.fragments_ids
        result = self._call(worker, fragmented_audio, library_data, fragment_ids)
        assert set(result.keys()) == set(fragment_ids)

    def test_same_inputs_produce_same_instructions(
        self,
        worker: ReconstructorWorker,
        fragmented_audio: Any,
        library_data: InstructionLibraryData,
    ) -> None:
        fragment_ids = [fragmented_audio.fragments_ids[0]]
        result_a = self._call(worker, fragmented_audio, library_data, fragment_ids)
        result_b = self._call(worker, fragmented_audio, library_data, fragment_ids)
        for generator_name in result_a[fragment_ids[0]]:
            assert (
                result_a[fragment_ids[0]][generator_name].instruction
                == result_b[fragment_ids[0]][generator_name].instruction
            )
