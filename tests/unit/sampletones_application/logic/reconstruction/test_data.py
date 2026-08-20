from pathlib import Path
from typing import Callable

import numpy as np

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_core.audio import load_audio, mix_audios, write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction


class TestFromReconstruction:
    def test_wraps_the_same_object_for_live_linking(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()

        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        assert data.reconstruction is reconstruction

    def test_has_no_filepath_for_in_memory_reconstruction(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()

        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )
        assert data.filepath is None

    def test_uses_the_supplied_display_name(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        data = ReconstructionData.from_reconstruction(
            reconstruction_factory(),
            name="Kick drum",
        )
        assert data.name == "Kick drum"

    def test_detached_reconstruction_has_no_original_audio(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction.detach_source()

        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        assert reconstruction.audio_filepath is None
        assert data.original_audio is None

    def test_loads_original_audio_when_source_file_is_available(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        source_audio = tmp_path / "source.wav"
        write_wave(
            source_audio,
            Config().library.sample_rate,
            np.ones(64, dtype=np.float32) * 0.5,
        )
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": source_audio})

        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        assert data.original_audio is not None

    def test_mixes_several_recorded_paths_into_the_original(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        config = Config()
        first = tmp_path / "kick.wav"
        second = tmp_path / "snare.wav"
        write_wave(first, config.library.sample_rate, np.ones(64, dtype=np.float32) * 0.5)
        write_wave(second, config.library.sample_rate, np.ones(64, dtype=np.float32) * 0.25)
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": (first, second)})

        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        load_options = {
            "target_sample_rate": config.library.sample_rate,
            "normalize": config.general.normalize,
            "quantize": config.general.quantize,
        }
        expected = mix_audios(
            [
                load_audio(path=first, **load_options),
                load_audio(path=second, **load_options),
            ]
        )
        assert data.original_audio is not None
        np.testing.assert_allclose(data.original_audio, expected)

    def test_one_unreadable_stem_costs_the_whole_original(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        first = tmp_path / "kick.wav"
        missing = tmp_path / "gone.wav"
        write_wave(first, Config().library.sample_rate, np.ones(64, dtype=np.float32) * 0.5)
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": (first, missing)})

        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        assert data.original_audio is None


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

    def test_load_has_no_original_audio_when_source_file_missing(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction = reconstruction_factory()
        save_path = tmp_path / "song.stn"
        reconstruction.save(save_path)

        data = ReconstructionData.load(save_path)

        assert data.original_audio is None


class TestDetachedCopy:
    def test_produces_a_distinct_reconstruction_object(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        copy = data.detached_copy(tmp_path / "lead.stn")

        assert copy.reconstruction is not reconstruction

    def test_is_file_backed_at_the_target_path(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        data = ReconstructionData.from_reconstruction(
            reconstruction_factory(),
            name="Sample",
        )
        target = tmp_path / "lead.stn"

        copy = data.detached_copy(target)

        assert copy.filepath == target

    def test_names_after_the_file_when_audio_is_detached(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction.detach_source()
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        copy = data.detached_copy(tmp_path / "lead.stn")

        assert copy.name == "lead"

    def test_names_after_the_source_audio_when_present(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        copy = data.detached_copy(tmp_path / "lead.stn")

        assert reconstruction.audio_filepath is not None
        assert copy.name == reconstruction.audio_filepath.stem

    def test_names_after_the_shared_directory_of_stems(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        drums = tmp_path / "drums"
        drums.mkdir()
        stems = (drums / "kick.wav", drums / "snare.wav")
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": stems})
        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        copy = data.detached_copy(tmp_path / "lead.stn")

        assert copy.name == "drums"

    def test_names_after_the_file_when_stems_share_no_directory(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        (tmp_path / "one").mkdir()
        (tmp_path / "two").mkdir()
        stems = (tmp_path / "one" / "kick.wav", tmp_path / "two" / "snare.wav")
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": stems})
        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        copy = data.detached_copy(tmp_path / "lead.stn")

        assert copy.name == "lead"

    def test_reuses_the_already_loaded_original_audio(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        source_audio = tmp_path / "source.wav"
        write_wave(
            source_audio,
            Config().library.sample_rate,
            np.ones(64, dtype=np.float32) * 0.5,
        )
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": source_audio})
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        copy = data.detached_copy(tmp_path / "lead.stn")

        assert data.original_audio is not None
        assert copy.original_audio is data.original_audio


class TestWaveformData:
    def test_projects_the_render_relevant_fields(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

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
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        result = data.get_partials([])

        assert np.all(result == 0.0)

    def test_unknown_generator_returns_zeros(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        result = data.get_partials([ChannelName.TRIANGLE])

        assert np.all(result == 0.0)

    def test_known_generator_returns_its_approximation(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        result = data.get_partials([ChannelName.PULSE1])

        expected = reconstruction.approximations[ChannelName.PULSE1]
        assert np.array_equal(result, expected)
