from typing import Any, List

import numpy as np
import pytest

from sampletones_application.services.regeneration import RegenerationService
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_core.constants.enums import FeatureKey, GeneratorName


class TestRegenerationServicePipeline:
    """Full synthesis pipeline: real Config, Features (via PulseExporter), real PulseGenerator,
    and real Reconstruction.update_generator_data. Nothing is mocked.

    Tests call _run() directly to bypass the executor; the synchronous_executor fixture
    from the parent conftest covers start() in the final test.
    """

    def test_run_emits_service_success(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)

    def test_run_emits_new_reconstruction_carrying_the_edit(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        emitted = results[0].value
        assert emitted is not reconstruction_data.reconstruction
        assert len(emitted.get_generator_approximation(GeneratorName.PULSE1)) > 0

    def test_run_updates_reconstruction_approximation(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        approximation = reconstruction_data.reconstruction.get_generator_approximation(GeneratorName.PULSE1)
        assert len(approximation) > 0

    def test_run_updates_reconstruction_instructions(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        instructions = reconstruction_data.reconstruction.get_generator_instructions(GeneratorName.PULSE1)
        assert len(instructions) > 0

    def test_run_feature_mutation_is_applied_before_synthesis(self, reconstruction_data, pulse_features) -> None:
        new_volume = np.zeros(len(pulse_features.volume), dtype=np.int8)
        service = RegenerationService()

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            new_volume,
        )

        assert (pulse_features.volume == new_volume).all()

    def test_run_emits_service_error_for_wrong_features_type(self, reconstruction_data) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            {},
            FeatureKey.VOLUME,
            np.zeros(4, dtype=np.int8),
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceError)

    def test_start_completes_through_full_pipeline(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service.start(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)
