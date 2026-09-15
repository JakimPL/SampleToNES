from __future__ import annotations

from typing import Dict, Final

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.array import to_numpy

WORKER_SIGNAL_LENGTH: Final[int] = 1 << 20
DRIVE: Final[float] = 2.0


def _driven_worker(
    config: Config,
    window: Window,
    channels: Dict[ChannelName, GeneratorUnion],
    library_data: InstructionLibraryData,
) -> ReconstructorWorker:
    driven = config.model_copy(update={"generation": config.generation.model_copy(update={"drive": DRIVE})})
    return ReconstructorWorker(
        config=driven,
        window=window,
        channels=channels,
        library_data=library_data,
        signal_length=WORKER_SIGNAL_LENGTH,
    )


class TestCandidatePowers:
    def test_a_power_reads_back_as_the_feature_it_came_from(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
    ) -> None:
        provider = worker.candidate_provider

        feature = to_numpy(provider.features_of(provider.power_of(audible_instruction)[None, :]))[0]

        np.testing.assert_allclose(feature, library_data[audible_instruction].feature.values, rtol=1e-4, atol=1e-9)

    def test_a_driven_power_reads_back_as_the_amplified_feature(
        self,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
    ) -> None:
        provider = _driven_worker(config, window, channels, library_data).candidate_provider
        extractor = get_feature_extractor(config, window)
        amplified = extractor.amplified(library_data[audible_instruction].get_fragment(0, config, window), DRIVE)

        feature = to_numpy(provider.features_of(provider.power_of(audible_instruction)[None, :]))[0]

        np.testing.assert_allclose(feature, amplified.feature.values, rtol=1e-4, atol=1e-9)

    def test_every_candidate_of_a_class_holds_a_row_of_power(
        self,
        worker: ReconstructorWorker,
        channels: Dict[ChannelName, GeneratorUnion],
    ) -> None:
        pulse = channels[ChannelName.PULSE1]

        candidates = worker.candidate_provider.candidates({pulse.class_name(): pulse})

        powers = to_numpy(candidates.powers)
        assert powers.shape == (len(candidates.instructions), worker.candidate_provider.widths.shape[0])
        for instruction, row in zip(candidates.instructions, powers):
            np.testing.assert_allclose(row, worker.candidate_provider.power_of(instruction))
