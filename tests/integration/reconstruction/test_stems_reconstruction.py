from pathlib import Path
from typing import AbstractSet, Dict, Final

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_core.audio import load_audio, mix, write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from tests.integration.assets.reconstruction import (
    STEM_A_ID,
    STEM_B_ID,
    STEM_C_ID,
    build_mini_library,
    three_stem_config,
    three_stem_reconstruction_config,
    write_three_stem_recordings,
)

_TONE_FREQUENCY: Final[float] = 440.0
_DURATION_SECONDS: Final[float] = 0.5
_MIX_TOLERANCE: Final[float] = 1e-6  # float32 sums drift with accumulation order


def _stems_config() -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(id=0, channels=[ChannelName.PULSE1]),
            StemEntry(id=1, channels=[ChannelName.NOISE]),
        ],
        hierarchy=StemsHierarchy(
            levels=[[0], [1]],
            mode=HierarchyMode.STRICT,
        ),
        channel_cap=1,
    )


class TestReconstructStems:
    def test_assigns_disjoint_stems_to_their_channels(self, tmp_path: Path) -> None:
        config = Config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)

        sample_rate = config.library.sample_rate
        count = int(sample_rate * _DURATION_SECONDS)
        time = np.arange(count) / sample_rate
        tone = 0.5 * np.sin(2 * np.pi * _TONE_FREQUENCY * time)
        rng = np.random.default_rng(93)
        noise = rng.uniform(-0.3, 0.3, count)

        tone_path = tmp_path / "tone.wav"
        noise_path = tmp_path / "noise.wav"
        write_wave(tone_path, sample_rate, tone)
        write_wave(noise_path, sample_rate, noise)

        reconstruction = reconstructor.reconstruct_stems(
            [tone_path, noise_path],
            _stems_config(),
        )

        assert reconstruction is not None
        assert reconstruction.audio_filepath == (tone_path, noise_path)
        assert reconstruction.stems_data is not None
        stems_data = reconstruction.stems_data
        assert stems_data.config == _stems_config()
        assert {entry.id for entry in stems_data.config.entries} == {0, 1}

        assignments = stems_data.assignments_by_channel
        assert set(assignments) == {
            ChannelName.PULSE1,
            ChannelName.NOISE,
        }
        assert set(assignments[ChannelName.PULSE1]) == {0}
        assert set(assignments[ChannelName.NOISE]) == {1}

        frame_count = count // config.library.frame_length
        assert len(assignments[ChannelName.PULSE1]) == frame_count
        assert len(assignments[ChannelName.NOISE]) == frame_count
        assert len(reconstruction.instructions[ChannelName.PULSE1]) == frame_count
        assert len(reconstruction.instructions[ChannelName.NOISE]) == frame_count

    def test_requires_one_path_per_entry(self, tmp_path: Path) -> None:
        config = Config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)

        with pytest.raises(ValueError, match="stem paths"):
            reconstructor.reconstruct_stems(
                [tmp_path / "only_one.wav"],
                _stems_config(),
            )


class TestThreeStemHierarchy:
    """The shared three-stem example: a (pulse 1, triangle, noise) and b (pulse 2,
    triangle) pick on the first hierarchy level, c (pulse 1, noise) on the second."""

    def test_builds_a_reconstruction_over_the_three_stems(self, tmp_path: Path) -> None:
        config = three_stem_reconstruction_config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)
        stems_config = three_stem_config()
        paths = write_three_stem_recordings(config, tmp_path)

        reconstruction = reconstructor.reconstruct_stems(list(paths), stems_config)

        assert reconstruction is not None
        assert reconstruction.audio_filepath == paths
        stems_data = reconstruction.stems_data
        assert stems_data is not None
        assert stems_data.config == stems_config

        assignments = stems_data.assignments_by_channel
        assert assignments
        assert set(assignments.get(ChannelName.PULSE2, [])) == {STEM_B_ID}
        assert set(assignments.get(ChannelName.TRIANGLE, [])) <= {STEM_A_ID, STEM_B_ID}
        assert set(assignments.get(ChannelName.PULSE1, [])) <= {STEM_A_ID, STEM_C_ID}
        assert set(assignments.get(ChannelName.NOISE, [])) <= {STEM_A_ID, STEM_C_ID}
        for channel, stem_ids in assignments.items():
            assert len(reconstruction.instructions[channel]) == len(stem_ids)

    def test_round_trips_through_the_file(self, tmp_path: Path) -> None:
        config = three_stem_reconstruction_config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)
        stems_config = three_stem_config()
        paths = write_three_stem_recordings(config, tmp_path)
        reconstruction = reconstructor.reconstruct_stems(list(paths), stems_config)
        assert reconstruction is not None

        save_path = tmp_path / "three_stems.stn"
        reconstruction.save(save_path)

        loaded = Reconstruction.load(save_path)

        assert loaded.source_paths == paths
        assert loaded.stems_data is not None
        assert loaded.stems_data.config == stems_config
        assert loaded.stems_data.assignments_by_channel == reconstruction.stems_data.assignments_by_channel

    def test_selection_filters_the_waveform_and_partials(self, tmp_path: Path) -> None:
        """Selecting stems zeroes the unselected stems' frames end to end.

        The loaded document projects the selection: each channel's waveform carries only the
        selected stems' frames, the partials sum them, the original plays the selected
        recordings, and a full selection answers the unfiltered audio.
        """
        config = three_stem_reconstruction_config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)
        stems_config = three_stem_config()
        paths = write_three_stem_recordings(config, tmp_path)
        reconstruction = reconstructor.reconstruct_stems(list(paths), stems_config)
        assert reconstruction is not None

        save_path = tmp_path / "three_stems.stn"
        reconstruction.save(save_path)
        data = ReconstructionData.load(save_path)
        stems_data = data.reconstruction.stems_data
        assert stems_data is not None

        frame_length = config.library.frame_length
        all_stem_ids = {entry.id for entry in stems_data.config.entries}
        channels = list(stems_data.assignments_by_channel)

        def masked_channels(selected: AbstractSet[int]) -> Dict[ChannelName, np.ndarray]:
            """The per-channel ground truth: the frames whose recorded stem id is selected."""
            masked: Dict[ChannelName, np.ndarray] = {}
            for channel, stem_ids in stems_data.assignments_by_channel.items():
                channel_audio = data.reconstruction.approximations[channel]
                frames = np.zeros_like(channel_audio)
                for frame_index, stem_id in enumerate(stem_ids):
                    if stem_id in selected:
                        start = frame_index * frame_length
                        frames[start : start + frame_length] = channel_audio[start : start + frame_length]
                masked[channel] = frames
            return masked

        unfiltered = data.waveform_data()
        full = data.waveform_data(frozenset(all_stem_ids))
        np.testing.assert_allclose(full.approximation, unfiltered.approximation, atol=_MIX_TOLERANCE)
        np.testing.assert_allclose(full.original_audio, unfiltered.original_audio, atol=_MIX_TOLERANCE)
        np.testing.assert_allclose(
            data.partials_for(channels, frozenset(all_stem_ids)),
            data.get_partials(channels),
            atol=_MIX_TOLERANCE,
        )

        for selected_id in (STEM_A_ID, STEM_B_ID, STEM_C_ID):
            selected = frozenset({selected_id})
            expected = masked_channels(selected)
            waveform = data.waveform_data(selected)

            for channel, expected_audio in expected.items():
                np.testing.assert_array_equal(waveform.approximations[channel], expected_audio)
            np.testing.assert_allclose(waveform.approximation, mix(list(expected.values())), atol=_MIX_TOLERANCE)
            np.testing.assert_allclose(
                data.partials_for(channels, selected),
                mix(list(expected.values())),
                atol=_MIX_TOLERANCE,
            )
            np.testing.assert_allclose(
                data.original_mix_for(selected), data.stem_audios[selected_id], atol=_MIX_TOLERANCE
            )

        selected = frozenset()
        waveform = data.waveform_data(selected)
        for channel in stems_data.assignments_by_channel:
            np.testing.assert_array_equal(
                waveform.approximations[channel],
                np.zeros_like(data.reconstruction.approximations[channel]),
            )
        np.testing.assert_allclose(waveform.approximation, np.zeros_like(data.reconstruction.approximation))
        np.testing.assert_allclose(
            data.partials_for(channels, selected),
            np.zeros_like(data.reconstruction.approximation),
        )
        np.testing.assert_allclose(
            data.original_mix_for(selected),
            np.zeros_like(data.reconstruction.approximation),
        )


class TestStemsOriginalAudio:
    def test_mixes_the_recorded_stems_into_one_original(self, tmp_path: Path) -> None:
        config = Config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)

        sample_rate = config.library.sample_rate
        count = int(sample_rate * _DURATION_SECONDS)
        time = np.arange(count) / sample_rate
        tone = 0.5 * np.sin(2 * np.pi * _TONE_FREQUENCY * time)
        rng = np.random.default_rng(93)
        noise = rng.uniform(-0.3, 0.3, count)

        tone_path = tmp_path / "tone.wav"
        noise_path = tmp_path / "noise.wav"
        write_wave(tone_path, sample_rate, tone)
        write_wave(noise_path, sample_rate, noise)

        reconstruction = reconstructor.reconstruct_stems(
            [tone_path, noise_path],
            _stems_config(),
        )
        assert reconstruction is not None

        save_path = tmp_path / "stems.stn"
        reconstruction.save(save_path)

        data = ReconstructionData.load(save_path)

        assert data.reconstruction.source_paths == (tone_path, noise_path)
        assert data.name == tmp_path.name
        load_options = {
            "target_sample_rate": config.library.sample_rate,
            "normalize": config.general.normalize,
            "quantize": config.general.quantize,
        }
        expected = mix(
            [
                load_audio(path=tone_path, **load_options),
                load_audio(path=noise_path, **load_options),
            ]
        )
        assert data.original_audio is not None
        np.testing.assert_allclose(data.original_audio, expected)
