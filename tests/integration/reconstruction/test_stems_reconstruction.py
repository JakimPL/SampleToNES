from pathlib import Path
from typing import AbstractSet, Dict, Final, Tuple

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_core.audio import load_audio, mix, write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import DEFAULT_STEMS_CHANNEL_CAP, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from tests.integration.assets.reconstruction import (
    STEM_A_ID,
    STEM_B_ID,
    STEM_C_ID,
    STEM_RECORDING_DURATION_SECONDS,
    build_mini_library,
    three_stem_config,
    three_stem_reconstruction_config,
    write_three_stem_recordings,
)

_TONE_FREQUENCY: Final[float] = 440.0
_DURATION_SECONDS: Final[float] = 0.5
_MIX_TOLERANCE: Final[float] = 1e-6  # float32 sums drift with accumulation order


def _frame_count(config: Config, duration_seconds: float) -> int:
    return int(config.library.sample_rate * duration_seconds) // config.library.frame_length


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

        reconstruction = reconstructor.reconstruct(
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
            reconstructor.reconstruct(
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

        reconstruction = reconstructor.reconstruct(list(paths), stems_config)

        assert reconstruction is not None
        assert reconstruction.audio_filepath == paths
        stems_data = reconstruction.stems_data
        assert stems_data is not None
        assert stems_data.config == stems_config

        assignments = stems_data.assignments_by_channel
        assert assignments
        holders = {
            ChannelName.PULSE2: {STEM_B_ID},
            ChannelName.TRIANGLE: {STEM_A_ID, STEM_B_ID},
            ChannelName.PULSE1: {STEM_A_ID, STEM_C_ID},
            ChannelName.NOISE: {STEM_A_ID, STEM_C_ID},
        }
        for channel, allowed in holders.items():
            assert set(assignments.get(channel, [])) - {RESTING_STEM_ID} <= allowed

        for channel, stem_ids in assignments.items():
            assert len(reconstruction.instructions[channel]) == len(stem_ids)

    def test_every_channel_in_play_carries_one_entry_per_frame(self, tmp_path: Path) -> None:
        """A cap leaves channels unclaimed, and each of them rests rather than dropping its frame.

        Streams that skipped a frame would carry their later frames early, so what a channel plays
        would drift out of step with the recording it was matched against.
        """
        config = three_stem_reconstruction_config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)
        stems_config = three_stem_config()
        paths = write_three_stem_recordings(config, tmp_path)

        reconstruction = reconstructor.reconstruct(list(paths), stems_config)

        assert reconstruction is not None
        frame_count = _frame_count(config, STEM_RECORDING_DURATION_SECONDS)
        assignments = reconstruction.stems_data.assignments_by_channel
        assert set(assignments) == set(reconstruction.playing_channels)

        for channel, stem_ids in assignments.items():
            assert len(stem_ids) == frame_count
            assert len(reconstruction.instructions[channel]) == frame_count
            assert len(reconstruction.approximations[channel]) == frame_count * config.library.frame_length

        picks_per_frame = [
            sum(stem_ids[frame] != RESTING_STEM_ID for stem_ids in assignments.values()) for frame in range(frame_count)
        ]
        assert picks_per_frame == [len(stems_config.entries)] * frame_count

    def test_round_trips_through_the_file(self, tmp_path: Path) -> None:
        config = three_stem_reconstruction_config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)
        stems_config = three_stem_config()
        paths = write_three_stem_recordings(config, tmp_path)
        reconstruction = reconstructor.reconstruct(list(paths), stems_config)
        assert reconstruction is not None

        save_path = tmp_path / "three_stems.stn"
        reconstruction.save(save_path)

        loaded = Reconstruction.load(save_path)

        assert loaded.audio_filepath == paths
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
        reconstruction = reconstructor.reconstruct(list(paths), stems_config)
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

        def heard(selected: AbstractSet[int]) -> StemSelection:
            """The selection hearing the named stems on every channel."""
            return StemSelection.everywhere(frozenset(selected), channels)

        unfiltered = data.waveform_data()
        full = data.waveform_data(heard(all_stem_ids))
        np.testing.assert_allclose(full.approximation, unfiltered.approximation, atol=_MIX_TOLERANCE)
        np.testing.assert_allclose(full.original_audio, unfiltered.original_audio, atol=_MIX_TOLERANCE)
        np.testing.assert_allclose(
            data.partials_for(channels, heard(all_stem_ids)),
            data.get_partials(channels),
            atol=_MIX_TOLERANCE,
        )

        for selected_id in (STEM_A_ID, STEM_B_ID, STEM_C_ID):
            selected = frozenset({selected_id})
            expected = masked_channels(selected)
            waveform = data.waveform_data(heard(selected))

            for channel, expected_audio in expected.items():
                np.testing.assert_array_equal(waveform.approximations[channel], expected_audio)
            np.testing.assert_allclose(waveform.approximation, mix(list(expected.values())), atol=_MIX_TOLERANCE)
            np.testing.assert_allclose(
                data.partials_for(channels, heard(selected)),
                mix(list(expected.values())),
                atol=_MIX_TOLERANCE,
            )
            np.testing.assert_allclose(
                data.original_mix_for(heard(selected)), data.stem_audios[selected_id], atol=_MIX_TOLERANCE
            )

        selected = frozenset()
        waveform = data.waveform_data(heard(selected))
        for channel in stems_data.assignments_by_channel:
            np.testing.assert_array_equal(
                waveform.approximations[channel],
                np.zeros_like(data.reconstruction.approximations[channel]),
            )
        np.testing.assert_allclose(waveform.approximation, np.zeros_like(data.reconstruction.approximation))
        np.testing.assert_allclose(
            data.partials_for(channels, heard(selected)),
            np.zeros_like(data.reconstruction.approximation),
        )
        np.testing.assert_allclose(
            data.original_mix_for(heard(selected)),
            np.zeros_like(data.reconstruction.approximation),
        )


class TestRemovingAStem:
    """The shared three-stem example with one recording taken out of the document for good."""

    def _three_stems(self, tmp_path: Path) -> Tuple[Reconstruction, Tuple[Path, Path, Path], Config]:
        config = three_stem_reconstruction_config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)
        paths = write_three_stem_recordings(config, tmp_path)
        reconstruction = reconstructor.reconstruct(list(paths), three_stem_config())
        assert reconstruction is not None
        return reconstruction, paths, config

    def test_the_removed_recording_leaves_the_setup_and_the_source_paths(self, tmp_path: Path) -> None:
        reconstruction, paths, _config = self._three_stems(tmp_path)

        remaining = without_stem(reconstruction, STEM_C_ID)

        assert [entry.id for entry in remaining.stems_data.config.entries] == [STEM_A_ID, STEM_B_ID]
        assert remaining.stems_data.config.hierarchy.levels == [[STEM_A_ID, STEM_B_ID]]
        assert remaining.audio_filepath == (paths[0], paths[1])

    def test_the_frames_it_held_fall_silent_while_the_rest_stand(self, tmp_path: Path) -> None:
        """A removal touches the removed recording's frames alone, sample for sample."""
        reconstruction, _paths, config = self._three_stems(tmp_path)
        frame_length = config.library.frame_length
        assignments = reconstruction.stems_data.assignments_by_channel
        before = {channel: audio.copy() for channel, audio in reconstruction.approximations.items()}

        remaining = without_stem(reconstruction, STEM_C_ID)

        for channel, stem_ids in assignments.items():
            audio = remaining.approximations[channel]
            for frame_index, stem_id in enumerate(stem_ids):
                span = slice(frame_index * frame_length, (frame_index + 1) * frame_length)
                expected = np.zeros(frame_length, dtype=np.float32) if stem_id == STEM_C_ID else before[channel][span]
                np.testing.assert_array_equal(audio[span], expected)

            assert remaining.stems_data.assignments_by_channel[channel] == [
                RESTING_STEM_ID if stem_id == STEM_C_ID else stem_id for stem_id in stem_ids
            ]

    def test_the_channels_it_alone_held_stand_by(self, tmp_path: Path) -> None:
        """Under a cap of one, stem c alone sounds pulse 1 and noise, so both fall quiet with it.

        A channel every remaining recording passes over describes no frame at all, which is what
        tells it apart from a channel that plays.
        """
        reconstruction, _paths, _config = self._three_stems(tmp_path)

        remaining = without_stem(reconstruction, STEM_C_ID)

        assert remaining.playing_channels == (ChannelName.PULSE2, ChannelName.TRIANGLE)
        for channel in (ChannelName.PULSE1, ChannelName.NOISE):
            np.testing.assert_array_equal(
                remaining.approximations[channel],
                np.zeros_like(reconstruction.approximations[channel]),
            )
            assert set(remaining.stems_data.assignments_by_channel[channel]) == {RESTING_STEM_ID}

    def test_the_reduced_reconstruction_round_trips_through_the_file(self, tmp_path: Path) -> None:
        reconstruction, _paths, _config = self._three_stems(tmp_path)
        remaining = without_stem(reconstruction, STEM_B_ID)
        save_path = tmp_path / "two_stems.stn"

        remaining.save(save_path)
        loaded = Reconstruction.load(save_path)

        assert [entry.id for entry in loaded.stems_data.config.entries] == [STEM_A_ID, STEM_C_ID]
        assert loaded.stems_data.config.hierarchy.levels == [[STEM_A_ID], [STEM_C_ID]]
        np.testing.assert_allclose(loaded.approximation, remaining.approximation, atol=_MIX_TOLERANCE)

    def test_what_stays_plays_as_it_did_before(self, tmp_path: Path) -> None:
        """A removal leaves the same audio the reader heard while listening to the stems that stay."""
        reconstruction, _paths, _config = self._three_stems(tmp_path)
        data = ReconstructionData.from_reconstruction(reconstruction, name="three")
        channels = list(reconstruction.stems_data.assignments_by_channel)
        heard_before = data.waveform_data(
            StemSelection.everywhere(frozenset({STEM_A_ID, STEM_B_ID}), channels)
        ).approximation

        remaining = without_stem(reconstruction, STEM_C_ID)
        reduced = ReconstructionData.from_reconstruction(remaining, name="two")
        heard_after = reduced.waveform_data(
            StemSelection.everywhere(frozenset({STEM_A_ID, STEM_B_ID}), channels)
        ).approximation

        np.testing.assert_allclose(heard_after, heard_before, atol=_MIX_TOLERANCE)


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

        reconstruction = reconstructor.reconstruct(
            [tone_path, noise_path],
            _stems_config(),
        )
        assert reconstruction is not None

        save_path = tmp_path / "stems.stn"
        reconstruction.save(save_path)

        data = ReconstructionData.load(save_path)

        assert data.reconstruction.audio_filepath == (tone_path, noise_path)
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


class TestClassicRunCarriesTheSingleEntryRecord:
    """The classic single-file run is the stems pipeline's one-stem case."""

    def _tone_path(self, tmp_path: Path, config: Config) -> Path:
        sample_rate = config.library.sample_rate
        count = int(sample_rate * _DURATION_SECONDS)
        time = np.arange(count) / sample_rate
        tone = 0.5 * np.sin(2 * np.pi * _TONE_FREQUENCY * time)
        tone_path = tmp_path / "tone.wav"
        write_wave(tone_path, sample_rate, tone)
        return tone_path

    def test_classic_conversion_records_one_stem_over_every_enabled_channel(self, tmp_path: Path) -> None:
        config = Config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)
        tone_path = self._tone_path(tmp_path, config)

        reconstruction = reconstructor(tone_path)

        assert reconstruction is not None
        assert reconstruction.audio_filepath == (tone_path,)
        stems_data = reconstruction.stems_data
        assert stems_data.config.entries[0].id == 0
        assert stems_data.config.entries[0].channels == list(config.generation.channels)
        assert stems_data.config.channel_cap == DEFAULT_STEMS_CHANNEL_CAP
        for channel, stem_ids in stems_data.assignments_by_channel.items():
            assert set(stem_ids) <= {0}
            assert len(stem_ids) == len(reconstruction.instructions[channel])

    def test_a_cap_of_one_leaves_every_frame_to_one_channel(self, tmp_path: Path) -> None:
        """One channel sounds per frame while the others rest, each keeping its place in the frame."""
        config = Config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)
        tone_path = self._tone_path(tmp_path, config)

        reconstruction = reconstructor.reconstruct(
            [tone_path],
            StemsConfig.single_entry(list(config.generation.channels), channel_cap=1),
        )

        assert reconstruction is not None
        assignments = reconstruction.stems_data.assignments_by_channel
        frame_count = _frame_count(config, _DURATION_SECONDS)

        for channel, stem_ids in assignments.items():
            assert set(stem_ids) <= {0, RESTING_STEM_ID}
            assert len(stem_ids) == frame_count
            assert len(reconstruction.instructions[channel]) == frame_count

        sounding = [sum(stem_ids[frame] == 0 for stem_ids in assignments.values()) for frame in range(frame_count)]
        assert sounding == [1] * frame_count
