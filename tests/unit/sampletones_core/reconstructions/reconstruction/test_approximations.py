from typing import Dict, Final, FrozenSet, Mapping, Sequence

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_STEM_ID, UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.generators.render import render_channels, render_instructions
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.filter import filter_approximations
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
LOUD_DRIVE: Final[float] = 2.0
STORED_AUDIO_KEYS: Final[FrozenSet[str]] = frozenset({"approximation", "approximations_data"})


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0)


def _silence() -> PulseInstruction:
    return PulseInstruction.null_instruction()


def _config() -> Config:
    return Config()


def _stems_config(*, loud_channel_drive: float) -> StemsConfig:
    """Two recordings over the first pulse, the first pushing it harder than the second."""
    channels = [ChannelName.PULSE1]
    return StemsConfig(
        entries=[
            StemEntry(
                id=STEM_A,
                settings=StemSettings(
                    channels=channels,
                    bends=bending_channels(channels),
                    drives={ChannelName.PULSE1: loud_channel_drive},
                    channel_cap=1,
                ),
            ),
            StemEntry(
                id=STEM_B,
                settings=StemSettings(
                    channels=channels,
                    bends=bending_channels(channels),
                    drives={ChannelName.PULSE1: UNIT_DRIVE},
                    channel_cap=1,
                ),
            ),
        ],
        hierarchy=StemsHierarchy(levels=[[STEM_A], [STEM_B]]),
    )


def _reconstruction(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    owners: Mapping[ChannelName, Sequence[int]],
    *,
    loud_channel_drive: float = LOUD_DRIVE,
) -> Reconstruction:
    return Reconstruction.create(
        instructions=instructions,
        config=_config(),
        coefficient=1.0,
        audio_filepath=(),
        stems_data=StemsData(
            config=_stems_config(loud_channel_drive=loud_channel_drive),
            assignments=[
                ChannelAssignment(channel_name=channel_name, stem_ids=list(stem_ids))
                for channel_name, stem_ids in owners.items()
            ],
        ),
    )


def _frame(audio: np.ndarray, index: int) -> np.ndarray:
    frame_length = _config().library.frame_length
    return audio[index * frame_length : (index + 1) * frame_length]


@pytest.fixture
def reconstruction() -> Reconstruction:
    """Three pulse frames: the first recording holds the first, the second the next, and the last rests."""
    return _reconstruction(
        {ChannelName.PULSE1: [_pulse(60), _pulse(62), _silence()]},
        {ChannelName.PULSE1: [STEM_A, STEM_B, RESTING_STEM_ID]},
    )


class TestTheAudioAReconstructionAnswersWith:
    """A channel sounds what its generator renders from the stream it carries, drive or none."""

    def test_a_channel_sounds_exactly_what_its_instructions_render(
        self,
        reconstruction: Reconstruction,
    ) -> None:
        """The document behind this stands at a drive off unit, and sounds its instructions all the same."""
        rendered = render_channels(reconstruction.instructions, reconstruction.config)

        np.testing.assert_array_equal(reconstruction.approximations[ChannelName.PULSE1], rendered[ChannelName.PULSE1])

    def test_a_resting_frame_sounds_nothing(self, reconstruction: Reconstruction) -> None:
        np.testing.assert_array_equal(
            _frame(reconstruction.approximations[ChannelName.PULSE1], 2),
            np.zeros(reconstruction.config.library.frame_length, dtype=np.float32),
        )

    def test_a_channel_standing_by_sounds_nothing_at_all(self) -> None:
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [_pulse(60)]},
            {ChannelName.PULSE1: [STEM_A]},
        )

        assert ChannelName.TRIANGLE not in reconstruction.approximations


class TestWhatTheFileCarries:
    def test_the_written_form_names_the_instructions_and_leaves_the_audio_out(
        self,
        reconstruction: Reconstruction,
    ) -> None:
        written = reconstruction.serialize_inner()

        assert "instructions_data" in written
        assert STORED_AUDIO_KEYS.isdisjoint(written)

    def test_a_reconstruction_sounds_the_same_after_a_round_trip(self, reconstruction: Reconstruction) -> None:
        restored = Reconstruction.deserialize(reconstruction.serialize())

        np.testing.assert_array_equal(
            restored.approximations[ChannelName.PULSE1],
            reconstruction.approximations[ChannelName.PULSE1],
        )


class TestAFilteredReading:
    """Filtering masks a whole channel's render, which is what keeps the oscillator where it stood."""

    @staticmethod
    def _kept(reconstruction: Reconstruction, stem_ids: Sequence[int]) -> Dict[ChannelName, np.ndarray]:
        selection = StemSelection(channels={ChannelName.PULSE1: frozenset(stem_ids)})
        return filter_approximations(
            reconstruction.stems_data,
            reconstruction.approximations,
            selection,
            reconstruction.config.library.frame_length,
        )

    def test_a_kept_frame_carries_the_samples_the_whole_render_gave_it(
        self,
        reconstruction: Reconstruction,
    ) -> None:
        filtered = self._kept(reconstruction, [STEM_B])

        np.testing.assert_array_equal(
            _frame(filtered[ChannelName.PULSE1], 1),
            _frame(reconstruction.approximations[ChannelName.PULSE1], 1),
        )

    def test_a_frame_left_out_falls_silent(self, reconstruction: Reconstruction) -> None:
        filtered = self._kept(reconstruction, [STEM_B])

        np.testing.assert_array_equal(
            _frame(filtered[ChannelName.PULSE1], 0),
            np.zeros(reconstruction.config.library.frame_length, dtype=np.float32),
        )

    def test_a_held_note_kept_from_its_second_frame_stands_where_the_whole_render_left_it(self) -> None:
        """Rendering the kept frames alone would restart the oscillator, so filtering renders the whole stream."""
        held = _reconstruction(
            {ChannelName.PULSE1: [_pulse(60), _pulse(60)]},
            {ChannelName.PULSE1: [STEM_A, STEM_B]},
            loud_channel_drive=UNIT_DRIVE,
        )
        alone = render_instructions([_pulse(60)], ChannelName.PULSE1, held.config)

        filtered = self._kept(held, [STEM_B])

        np.testing.assert_array_equal(
            _frame(filtered[ChannelName.PULSE1], 1),
            _frame(held.approximations[ChannelName.PULSE1], 1),
        )
        assert not np.array_equal(_frame(filtered[ChannelName.PULSE1], 1), alone)

    def test_every_channel_the_record_names_comes_back(self, reconstruction: Reconstruction) -> None:
        filtered = self._kept(reconstruction, [STEM_A, STEM_B])

        assert list(filtered) == [ChannelName.PULSE1]


class TestTheChannelsAReconstructionPlays:
    def test_a_channel_whose_stream_describes_a_frame_plays(self) -> None:
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [_pulse(60)]},
            {ChannelName.PULSE1: [STEM_A]},
        )

        assert reconstruction.playing_channels == (ChannelName.PULSE1,)

    def test_the_mixed_audio_sums_the_channels_that_play(self) -> None:
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [_pulse(60)]},
            {ChannelName.PULSE1: [STEM_A]},
        )

        np.testing.assert_array_equal(
            reconstruction.approximation,
            reconstruction.approximations[ChannelName.PULSE1],
        )
