from pathlib import Path
from typing import Final, List

import pytest

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.constants.algorithm import ALL_STEMS_CHANNEL_CAP, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.application import SAMPLETONES_RECONSTRUCTION_DATA_VERSION
from tests.suite.compatibility import RECONSTRUCTION_VERSION, archived

SOURCE_PATH: Final[Path] = Path("samples") / "kick.wav"
SOURCE_NAME: Final[str] = "kick"
SINGLE_STEM_ID: Final[int] = 0
FRAMES: Final[int] = 3
STORED_DRIVE: Final[float] = 1.5


@pytest.fixture(name="validated")
def validated_fixture() -> Reconstruction:
    """The archived file read with every rule the model states held to it."""
    return Reconstruction.load(archived(ObjectKind.RECONSTRUCTION, RECONSTRUCTION_VERSION), fast=False)


@pytest.fixture(name="loaded")
def loaded_fixture() -> Reconstruction:
    """The archived file read the way the application reads one, which asks for no validation."""
    return Reconstruction.load(archived(ObjectKind.RECONSTRUCTION, RECONSTRUCTION_VERSION))


class TestTheVersionAnUpgradedFileStates:
    """A file carried forward states the version its shape now matches, inside and out."""

    def test_the_file_states_the_version_this_build_reads(self, validated: Reconstruction) -> None:
        assert validated.metadata.reconstruction_data_version == SAMPLETONES_RECONSTRUCTION_DATA_VERSION

    def test_the_configuration_it_carries_states_it_too(self, validated: Reconstruction) -> None:
        assert validated.config.metadata.reconstruction_data_version == SAMPLETONES_RECONSTRUCTION_DATA_VERSION


class TestWhatAnUpgradedFileDescribes:
    """The channels, the frames and the instructions the archived file was written with stand."""

    def test_every_channel_it_was_written_with_plays(self, validated: Reconstruction) -> None:
        assert frozenset(validated.playing_channels) == frozenset(ChannelName.items())

    def test_each_channel_keeps_the_frames_it_was_written_with(self, validated: Reconstruction) -> None:
        assert all(len(validated.instructions[channel]) == FRAMES for channel in validated.playing_channels)

    def test_a_stream_reads_as_its_channel_sounds(self, validated: Reconstruction) -> None:
        """The streams were keyed by generator before 2.2, so this is the rename holding."""
        stream = validated.instructions[ChannelName.PULSE1]

        assert [instruction.on for instruction in stream] == [True, False, True]

    def test_the_audio_it_describes_renders(self, validated: Reconstruction) -> None:
        """A 2.2 file carries no audio, so the upgraded document must still be able to sound."""
        assert len(validated.approximation) == FRAMES * validated.config.frame_length


class TestTheRecordAnUpgradedFileGains:
    """A file written before the stems record gains the one a classic conversion would have written."""

    def test_the_record_names_one_recording(self, validated: Reconstruction) -> None:
        entries = validated.stems_data.config.entries

        assert len(entries) == 1
        assert entries[0].id == SINGLE_STEM_ID

    def test_the_recording_takes_the_channels_the_run_handed_out(self, validated: Reconstruction) -> None:
        settings = validated.stems_data.config.entries[0].settings

        assert frozenset(settings.channels) == frozenset(ChannelName.items())
        assert settings.channel_cap == ALL_STEMS_CHANNEL_CAP

    def test_the_drive_the_run_stored_reaches_every_channel(self, validated: Reconstruction) -> None:
        settings = validated.stems_data.config.entries[0].settings

        assert settings.drives == {channel_name: STORED_DRIVE for channel_name in settings.channels}

    def test_each_channel_names_one_owner_per_frame(self, validated: Reconstruction) -> None:
        for channel_name in validated.playing_channels:
            owners = validated.stems_data.assignments_by_channel[channel_name]
            assert len(owners) == len(validated.instructions[channel_name])

    def test_a_silent_frame_answers_to_rest(self, validated: Reconstruction) -> None:
        """Rest and silence name the same frames, which is the rule a stored record is held to."""
        for channel_name in validated.playing_channels:
            owners = validated.stems_data.assignments_by_channel[channel_name]
            stream = validated.instructions[channel_name]
            assert [owner == RESTING_STEM_ID for owner in owners] == [not item.on for item in stream]

    def test_a_sounding_frame_answers_to_the_recording(self, validated: Reconstruction) -> None:
        sounding: List[int] = [
            owner
            for channel_name in validated.playing_channels
            for owner in validated.stems_data.assignments_by_channel[channel_name]
            if owner != RESTING_STEM_ID
        ]

        assert sounding
        assert set(sounding) == {SINGLE_STEM_ID}


class TestTheRecordingAnUpgradedFileNames:
    """Where the audio came from travels onto the record, which is where a 2.2 file keeps it."""

    def test_the_file_still_names_its_recording(self, validated: Reconstruction) -> None:
        assert validated.audio_filepath == (SOURCE_PATH,)

    def test_the_record_names_the_recording_behind_the_one_entry(self, validated: Reconstruction) -> None:
        sources = validated.stems_data.sources

        assert [source.stem_id for source in sources] == [SINGLE_STEM_ID]
        assert validated.stems_data.named(SINGLE_STEM_ID) == SOURCE_NAME


class TestWhatTheApplicationGets:
    """The application asks for no validation, so what it gets is held to the rules by hand."""

    def test_it_reads_the_same_record(self, loaded: Reconstruction, validated: Reconstruction) -> None:
        assert loaded.stems_data.assignments_by_channel == validated.stems_data.assignments_by_channel

    def test_it_reads_the_same_recording(self, loaded: Reconstruction) -> None:
        assert loaded.audio_filepath == (SOURCE_PATH,)
