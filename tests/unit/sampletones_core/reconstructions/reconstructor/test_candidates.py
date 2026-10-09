from __future__ import annotations

from typing import Dict

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.array import to_numpy


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
