from pathlib import Path
from typing import Callable

import numpy as np

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_core.audio import load_audio, mix, write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy


def _heard(*stem_ids: int) -> StemSelection:
    """The selection hearing every named stem on every channel."""
    return StemSelection.everywhere(frozenset(stem_ids), ChannelName.items())


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

        assert reconstruction.audio_filepath == ()
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
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": (source_audio,)})

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
        expected = mix(
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

        assert reconstruction.audio_filepath
        assert copy.name == reconstruction.audio_filepath[0].stem

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

    def test_names_after_the_first_source_when_stems_share_no_directory(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        stems = (Path("/one/kick.wav"), Path("/two/snare.wav"))
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": stems})
        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        copy = data.detached_copy(tmp_path / "lead.stn")

        assert copy.name == "kick"

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
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": (source_audio,)})
        data = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )

        copy = data.detached_copy(tmp_path / "lead.stn")

        assert copy.stem_audios is data.stem_audios
        assert data.original_audio is not None
        np.testing.assert_allclose(copy.original_audio, data.original_audio)


class TestStemFilteredProjections:
    def _stems_data(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> ReconstructionData:
        config = Config()
        frame_length = config.library.frame_length
        length = 2 * frame_length
        approximation = np.arange(length, dtype=np.float32)
        stems_config = StemsConfig(
            entries=[
                StemEntry(id=0, channels=[ChannelName.PULSE1]),
                StemEntry(id=1, channels=[ChannelName.PULSE1]),
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1]]),
        )
        reconstruction = Reconstruction.create(
            approximation=approximation,
            approximations={ChannelName.PULSE1: approximation.copy()},
            instructions={ChannelName.PULSE1: [PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)] * 2},
            config=config,
            coefficient=1.0,
            audio_filepath=(tmp_path / "a.wav", tmp_path / "b.wav"),
            stems_data=StemsData(
                config=stems_config,
                assignments=[
                    ChannelAssignment(
                        channel_name=ChannelName.PULSE1,
                        stem_ids=[0, 1],
                    )
                ],
            ),
        )
        return ReconstructionData.from_reconstruction(reconstruction, name="Sample")

    def test_partials_keep_only_the_selected_stems_frames(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        data = self._stems_data(reconstruction_factory, tmp_path)
        frame_length = data.reconstruction.config.frame_length
        expected = data.reconstruction.approximation.copy()
        expected[frame_length:] = 0

        partials = data.partials_for([ChannelName.PULSE1], _heard(0))

        np.testing.assert_allclose(partials, expected)
        np.testing.assert_allclose(
            data.partials_for([ChannelName.PULSE1], _heard(0, 1)),
            data.reconstruction.approximation,
        )

    def test_original_mix_mixes_the_selected_recordings(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        first = tmp_path / "kick.wav"
        second = tmp_path / "snare.wav"
        write_wave(first, Config().library.sample_rate, np.ones(64, dtype=np.float32) * 0.5)
        write_wave(second, Config().library.sample_rate, np.ones(64, dtype=np.float32) * 0.25)
        stems_config = StemsConfig(
            entries=[
                StemEntry(id=0, channels=[ChannelName.PULSE1]),
                StemEntry(id=1, channels=[ChannelName.PULSE1]),
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1]]),
        )
        reconstruction = reconstruction_factory().model_copy(
            update={
                "audio_filepath": (first, second),
                "stems_data": StemsData(
                    config=stems_config,
                    assignments=[
                        ChannelAssignment(
                            channel_name=ChannelName.PULSE1,
                            stem_ids=[0, 1],
                        )
                    ],
                ),
            }
        )

        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        np.testing.assert_allclose(data.original_mix_for(_heard(0)), data.stem_audios[0])
        assert data.original_audio is not None
        np.testing.assert_allclose(data.original_mix_for(_heard(0, 1)), data.original_audio)
        np.testing.assert_array_equal(
            data.original_mix_for(_heard()),
            np.zeros_like(data.reconstruction.approximation),
        )

    def test_a_single_source_with_no_selection_is_silence(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        source_audio = tmp_path / "source.wav"
        write_wave(source_audio, Config().library.sample_rate, np.ones(64, dtype=np.float32) * 0.5)
        reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": (source_audio,)})

        data = ReconstructionData.from_reconstruction(reconstruction, name="Sample")

        np.testing.assert_array_equal(
            data.partials_for([ChannelName.PULSE1], _heard()),
            np.zeros_like(data.reconstruction.approximation),
        )
        assert data.original_audio is not None
        np.testing.assert_allclose(data.original_mix_for(_heard(0)), data.original_audio)


class TestRebindingToAnEditedReconstruction:
    def _three_recordings(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> ReconstructionData:
        """A document over three recordings, each carrying a shape of its own.

        The shapes differ rather than the levels, since loading normalises each recording and
        would read three levels of one shape as the same waveform.
        """
        sample_rate = Config().library.sample_rate
        shapes = (
            np.linspace(-1.0, 1.0, 64, dtype=np.float32),
            np.linspace(1.0, -1.0, 64, dtype=np.float32),
            np.concatenate([np.ones(32, dtype=np.float32), -np.ones(32, dtype=np.float32)]),
        )
        paths = []
        for index, shape in enumerate(shapes):
            path = tmp_path / f"stem_{index}.wav"
            write_wave(path, sample_rate, shape)
            paths.append(path)

        reconstruction = reconstruction_factory().model_copy(
            update={
                "audio_filepath": tuple(paths),
                "stems_data": StemsData(
                    config=StemsConfig(
                        entries=[StemEntry(id=stem_id, channels=[ChannelName.PULSE1]) for stem_id in range(3)],
                        hierarchy=StemsHierarchy(levels=[[0], [1], [2]]),
                    ),
                    assignments=[
                        ChannelAssignment(
                            channel_name=ChannelName.PULSE1,
                            stem_ids=[0],
                        )
                    ],
                ),
            }
        )
        return ReconstructionData.from_reconstruction(reconstruction, name="Sample")

    def test_a_recording_follows_the_entry_it_was_loaded_for(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        """A recording is read by position, so one entry leaving would slide the rest onto the wrong audio."""
        data = self._three_recordings(reconstruction_factory, tmp_path)
        third = data.stem_audios[2]

        remaining = data.with_reconstruction(without_stem(data.reconstruction, 1))

        np.testing.assert_allclose(remaining.original_mix_for(_heard(2)), third)

    def test_the_removed_recording_is_released(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        data = self._three_recordings(reconstruction_factory, tmp_path)
        second = data.stem_audios[1]

        remaining = data.with_reconstruction(without_stem(data.reconstruction, 1))

        assert len(remaining.stem_audios) == 2
        assert all(not np.array_equal(audio, second) for audio in remaining.stem_audios)

    def test_an_edit_keeping_every_entry_keeps_every_recording(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        data = self._three_recordings(reconstruction_factory, tmp_path)

        rebound = data.with_reconstruction(data.reconstruction.model_copy())

        assert rebound.stem_audios == data.stem_audios


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
