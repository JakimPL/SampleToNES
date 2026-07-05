from pathlib import Path
from typing import Callable, List

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.reconstructions import Reconstruction


class TestFromReconstruction:
    def test_wraps_the_same_object_for_live_linking(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()

        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        assert data.reconstruction is reconstruction

    def test_has_no_filepath_for_in_memory_reconstruction(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()

        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")
        assert data.filepath is None

    def test_uses_the_supplied_display_name(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        data = ReconstructionData.from_reconstruction(reconstruction_factory(), name="Kick drum")
        assert data.name == "Kick drum"

    def test_detached_reconstruction_yields_silent_original_audio(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction.detach_source()

        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        assert reconstruction.audio_filepath is None
        assert np.all(data.original_audio == 0.0)


class TestReconstructionDataLoad:
    def test_load_round_trips_reconstruction(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction = reconstruction_factory()
        save_path = tmp_path / "song.stn"
        reconstruction.save(save_path)

        data = ReconstructionData.load(save_path)

        assert data.filepath == save_path

    def test_load_falls_back_to_silent_audio_when_audio_file_missing(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction = reconstruction_factory()
        save_path = tmp_path / "song.stn"
        reconstruction.save(save_path)

        data = ReconstructionData.load(save_path)

        assert np.all(data.original_audio == 0.0)


class TestWaveformData:
    def test_projects_the_render_relevant_fields(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        waveform_data = data.waveform_data()

        assert waveform_data.original_audio is data.original_audio
        assert waveform_data.approximation is reconstruction.approximation
        assert waveform_data.approximations == dict(reconstruction.approximations)
        assert waveform_data.coefficient == reconstruction.coefficient
        assert waveform_data.frame_length == reconstruction.config.frame_length


class TestReconstructionDataGetPartials:
    def test_empty_generator_list_returns_zeros(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        result = data.get_partials([])

        assert np.all(result == 0.0)

    def test_unknown_generator_returns_zeros(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        result = data.get_partials([GeneratorName.TRIANGLE])

        assert np.all(result == 0.0)

    def test_known_generator_returns_its_approximation(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        result = data.get_partials([GeneratorName.PULSE1])

        expected = reconstruction.approximations[GeneratorName.PULSE1]
        assert np.array_equal(result, expected)
