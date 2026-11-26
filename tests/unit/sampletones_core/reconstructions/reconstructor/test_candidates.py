from __future__ import annotations

from typing import Dict

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.generation import SpectrumLayer
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.layers import analysis_layers
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
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


class TestALayeredProvider:
    """A candidate read in every layer's library holds each method's bins, in the order a frame stacks them."""

    @staticmethod
    @pytest.fixture(name="layered", scope="class")
    def layered_fixture(
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        library_data: InstructionLibraryData,
    ) -> ReconstructorWorker:
        """A worker reading the frames with ``logfft`` beside the test library's own method."""
        layered = config.model_copy(
            update={
                "generation": config.generation.model_copy(
                    update={"layers": (SpectrumLayer(method=SpectrumMethod.LOG_SPACED_FFT, weight=1.0),)}
                )
            }
        )
        _, added = analysis_layers(layered)
        generators = {generator.class_name(): generator for generator in channels.values()}
        logfft_data = InstructionLibraryData.create(
            added.config,
            {
                instruction: InstructionLibraryFragment.create(
                    generators[library_data[instruction].generator_class], instruction, added.extractor
                )
                for instruction in library_data.keys()
            },
        )
        return ReconstructorWorker(
            config=layered,
            window=window,
            channels=channels,
            library_data=library_data,
            layer_data=(logfft_data,),
            signal_length=config.library.frame_length,
        )

    def test_each_library_s_bins_follow_the_one_before(
        self, layered: ReconstructorWorker, library_data: InstructionLibraryData
    ) -> None:
        provider = layered.candidate_provider
        (logfft_data,) = layered.layer_data
        own, added = (len(next(iter(data.values())).feature.values) for data in (library_data, logfft_data))

        assert provider.sizes == (own, added)
        assert provider.widths.shape == (own + added,)

    def test_a_power_reads_back_as_every_library_s_feature_stacked(
        self, layered: ReconstructorWorker, library_data: InstructionLibraryData, audible_instruction: InstructionUnion
    ) -> None:
        provider = layered.candidate_provider
        (logfft_data,) = layered.layer_data

        feature = to_numpy(provider.features_of(provider.power_of(audible_instruction)[None, :]))[0]

        expected = np.concatenate(
            [library_data[audible_instruction].feature.values, logfft_data[audible_instruction].feature.values]
        )
        np.testing.assert_allclose(feature, expected, rtol=1e-4, atol=1e-9)
