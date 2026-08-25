from pathlib import Path
from typing import Dict, Final, List, Mapping, Sequence

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy

STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
STEM_C: Final[int] = 2
FRAME_COUNT: Final[int] = 4
PULSE_LEVEL: Final[float] = 3.0
NOISE_LEVEL: Final[float] = 2.0

RECORDINGS: Final[Dict[int, Path]] = {
    STEM_A: Path("/recordings/a.wav"),
    STEM_B: Path("/recordings/b.wav"),
    STEM_C: Path("/recordings/c.wav"),
}


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0)


def _noise() -> NoiseInstruction:
    return NoiseInstruction(on=True, period=4, volume=8, short=False)


def _stems_config() -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(id=STEM_A, channels=[ChannelName.PULSE1]),
            StemEntry(id=STEM_B, channels=[ChannelName.PULSE1, ChannelName.NOISE]),
            StemEntry(id=STEM_C, channels=[ChannelName.PULSE1]),
        ],
        hierarchy=StemsHierarchy(
            levels=[[STEM_A], [STEM_B, STEM_C]],
            mode=HierarchyMode.STRICT,
        ),
        channel_cap=1,
    )


def _reconstruction(
    owners: Mapping[ChannelName, Sequence[int]],
    *,
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    approximations: Mapping[ChannelName, np.ndarray],
) -> Reconstruction:
    """A three-recording reconstruction whose frames are owned as ``owners`` states."""
    return Reconstruction.create(
        approximation=np.zeros(0, dtype=np.float32),
        approximations=approximations,
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=tuple(RECORDINGS[stem_id] for stem_id in (STEM_A, STEM_B, STEM_C)),
        stems_data=StemsData(
            config=_stems_config(),
            assignments=[
                ChannelAssignment(channel_name=channel_name, stem_ids=list(stem_ids))
                for channel_name, stem_ids in owners.items()
            ],
        ),
    )


def _frame_length() -> int:
    return Config().library.frame_length


def _audio(level: float) -> np.ndarray:
    return np.full(FRAME_COUNT * _frame_length(), level, dtype=np.float32)


def _frame(audio: np.ndarray, index: int) -> np.ndarray:
    frame_length = _frame_length()
    return audio[index * frame_length : (index + 1) * frame_length]


def _sounding(reconstruction: Reconstruction, channel_name: ChannelName) -> List[bool]:
    """Whether each frame of a channel states a sounding instruction."""
    return [instruction.on for instruction in reconstruction.instructions[channel_name]]


@pytest.fixture
def reconstruction() -> Reconstruction:
    """Three recordings over two channels: the noise channel belongs to stem B throughout.

    Stem B holds the whole noise channel and the second pulse frame, so removing it both
    releases single frames and empties a channel — the two outcomes a removal has to answer.
    """
    return _reconstruction(
        {
            ChannelName.PULSE1: [STEM_A, STEM_B, STEM_C, RESTING_STEM_ID],
            ChannelName.NOISE: [STEM_B] * FRAME_COUNT,
        },
        instructions={
            ChannelName.PULSE1: [_pulse(60), _pulse(61), _pulse(62), _pulse(63)],
            ChannelName.NOISE: [_noise() for _ in range(FRAME_COUNT)],
        },
        approximations={
            ChannelName.PULSE1: _audio(PULSE_LEVEL),
            ChannelName.NOISE: _audio(NOISE_LEVEL),
        },
    )


class TestTheRecordedSetup:
    def test_the_removed_recording_leaves_the_entries(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_C)

        assert [entry.id for entry in remaining.stems_data.config.entries] == [STEM_A, STEM_B]

    def test_the_removed_recording_leaves_its_level(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_C)

        assert remaining.stems_data.config.hierarchy.levels == [[STEM_A], [STEM_B]]

    def test_a_level_the_removal_empties_goes_along_with_it(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_A)

        assert remaining.stems_data.config.hierarchy.levels == [[STEM_B, STEM_C]]

    def test_the_picking_order_and_the_cap_carry_over(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_C)

        assert remaining.stems_data.config.hierarchy.mode == HierarchyMode.STRICT
        assert remaining.stems_data.config.channel_cap == 1

    def test_the_removed_recordings_source_path_goes_from_its_position(
        self,
        reconstruction: Reconstruction,
    ) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        assert remaining.audio_filepath == (RECORDINGS[STEM_A], RECORDINGS[STEM_C])

    def test_a_detached_reconstruction_stays_detached(self, reconstruction: Reconstruction) -> None:
        reconstruction.detach_source()

        remaining = without_stem(reconstruction, STEM_B)

        assert remaining.audio_filepath == ()


class TestTheReleasedFrames:
    def test_the_frames_it_held_rest_in_the_assignment(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        assert remaining.stems_data.assignments_by_channel[ChannelName.PULSE1] == [
            STEM_A,
            RESTING_STEM_ID,
            STEM_C,
            RESTING_STEM_ID,
        ]

    def test_the_frames_it_held_state_silence(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        assert _sounding(remaining, ChannelName.PULSE1) == [True, False, True, True]

    def test_the_frames_it_held_lose_their_samples(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        audio = remaining.approximations[ChannelName.PULSE1]
        np.testing.assert_array_equal(_frame(audio, 1), np.zeros(_frame_length(), dtype=np.float32))

    def test_the_recordings_that_stay_keep_their_frames(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        audio = remaining.approximations[ChannelName.PULSE1]
        kept = np.full(_frame_length(), PULSE_LEVEL, dtype=np.float32)
        for index in (0, 2, 3):
            np.testing.assert_array_equal(_frame(audio, index), kept)

    def test_the_channel_keeps_its_length(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        assert len(remaining.approximations[ChannelName.PULSE1]) == FRAME_COUNT * _frame_length()

    def test_a_channel_the_removal_leaves_alone_keeps_its_audio(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_C)

        np.testing.assert_array_equal(
            remaining.approximations[ChannelName.NOISE],
            _audio(NOISE_LEVEL),
        )


class TestAnEmptiedChannel:
    def test_a_channel_left_entirely_released_stands_by(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        assert remaining.playing_channels == (ChannelName.PULSE1,)

    def test_a_channel_left_entirely_released_sounds_nothing(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        np.testing.assert_array_equal(
            remaining.approximations[ChannelName.NOISE],
            np.zeros(FRAME_COUNT * _frame_length(), dtype=np.float32),
        )

    def test_a_channel_left_entirely_released_rests_through_every_frame(
        self,
        reconstruction: Reconstruction,
    ) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        assert remaining.stems_data.assignments_by_channel[ChannelName.NOISE] == [RESTING_STEM_ID] * FRAME_COUNT

    def test_a_channel_that_already_rested_throughout_keeps_its_stream(self) -> None:
        """A removal reaching none of a channel's frames leaves that channel exactly as it stood."""
        reconstruction = _reconstruction(
            {
                ChannelName.PULSE1: [STEM_A, STEM_B, STEM_C, RESTING_STEM_ID],
                ChannelName.NOISE: [RESTING_STEM_ID] * FRAME_COUNT,
            },
            instructions={
                ChannelName.PULSE1: [_pulse(60), _pulse(61), _pulse(62), _pulse(63)],
                ChannelName.NOISE: [_noise() for _ in range(FRAME_COUNT)],
            },
            approximations={
                ChannelName.PULSE1: _audio(PULSE_LEVEL),
                ChannelName.NOISE: _audio(NOISE_LEVEL),
            },
        )

        remaining = without_stem(reconstruction, STEM_B)

        assert _sounding(remaining, ChannelName.NOISE) == [True] * FRAME_COUNT
        np.testing.assert_array_equal(remaining.approximations[ChannelName.NOISE], _audio(NOISE_LEVEL))

    def test_a_channel_an_edit_re_derived_keeps_its_stream(self) -> None:
        """A channel the assignment says nothing about is the editor's, so a removal passes it by."""
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [STEM_A, STEM_B, STEM_C, RESTING_STEM_ID]},
            instructions={
                ChannelName.PULSE1: [_pulse(60), _pulse(61), _pulse(62), _pulse(63)],
                ChannelName.NOISE: [_noise() for _ in range(FRAME_COUNT)],
            },
            approximations={
                ChannelName.PULSE1: _audio(PULSE_LEVEL),
                ChannelName.NOISE: _audio(NOISE_LEVEL),
            },
        )

        remaining = without_stem(reconstruction, STEM_B)

        assert _sounding(remaining, ChannelName.NOISE) == [True] * FRAME_COUNT
        np.testing.assert_array_equal(remaining.approximations[ChannelName.NOISE], _audio(NOISE_LEVEL))


class TestTheMixedApproximation:
    def test_the_mix_is_summed_afresh_from_what_stays(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_B)

        expected = np.full(FRAME_COUNT * _frame_length(), PULSE_LEVEL, dtype=np.float32)
        expected[_frame_length() : 2 * _frame_length()] = 0.0
        np.testing.assert_array_equal(remaining.approximation, expected)


class TestTheDocument:
    def test_the_document_keeps_its_identity(self, reconstruction: Reconstruction) -> None:
        remaining = without_stem(reconstruction, STEM_C)

        assert remaining.id == reconstruction.id
        assert remaining.config == reconstruction.config
        assert remaining.coefficient == reconstruction.coefficient
        assert remaining.metadata == reconstruction.metadata

    def test_the_source_reconstruction_is_left_as_it_stood(self, reconstruction: Reconstruction) -> None:
        without_stem(reconstruction, STEM_B)

        assert [entry.id for entry in reconstruction.stems_data.config.entries] == [STEM_A, STEM_B, STEM_C]
        assert reconstruction.stems_data.assignments_by_channel[ChannelName.NOISE] == [STEM_B] * FRAME_COUNT
        np.testing.assert_array_equal(reconstruction.approximations[ChannelName.NOISE], _audio(NOISE_LEVEL))


class TestARefusedRemoval:
    def test_removing_an_unrecorded_stem_is_refused(self, reconstruction: Reconstruction) -> None:
        with pytest.raises(ValueError, match="names no entry"):
            without_stem(reconstruction, 7)

    def test_removing_the_last_recording_is_refused(self) -> None:
        reconstruction = Reconstruction.create(
            approximation=np.zeros(0, dtype=np.float32),
            approximations={ChannelName.PULSE1: _audio(PULSE_LEVEL)},
            instructions={ChannelName.PULSE1: [_pulse(60)] * FRAME_COUNT},
            config=Config(),
            coefficient=1.0,
            audio_filepath=(RECORDINGS[STEM_A],),
            stems_data=StemsData.single_entry(
                [ChannelName.PULSE1],
                [
                    ChannelAssignment(
                        channel_name=ChannelName.PULSE1,
                        stem_ids=[STEM_A] * FRAME_COUNT,
                    )
                ],
            ),
        )

        with pytest.raises(ValueError, match="at least one stem"):
            without_stem(reconstruction, STEM_A)
