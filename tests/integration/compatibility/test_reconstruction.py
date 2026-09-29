from pathlib import Path
from typing import AbstractSet, Any, Dict, Final, List

import msgpack
import pytest

from sampletones_core.compatibility.fields import (
    GENERATOR_NAME,
    INSTRUCTION,
    INSTRUCTIONS,
    INSTRUCTIONS_DATA,
    ON,
    UNION_DATA,
)
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.constants.algorithm import ALL_STEMS_CHANNEL_CAP, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.application import SAMPLETONES_RECONSTRUCTION_DATA_VERSION
from tests.suite.compatibility import RECONSTRUCTION_VERSION, archived, stored_document

SOURCE_PATH: Final[Path] = Path("samples") / "kick.wav"
SOURCE_NAME: Final[str] = "kick"
SINGLE_STEM_ID: Final[int] = 0
FRAMES: Final[int] = 3
STORED_DRIVE: Final[float] = 1.5
SILENCED_CHANNEL: Final[ChannelName] = ChannelName.PULSE1


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


class TestTheScaleAnUpgradedFileStates:
    """A file the last release wrote kept no scale, and its one recording reads at its own peak."""

    def test_the_record_states_no_scale(self, validated: Reconstruction) -> None:
        assert validated.stems_data.scale is None

    def test_the_application_reads_the_same(self, loaded: Reconstruction) -> None:
        assert loaded.stems_data.scale is None


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


def _silenced(document: Dict[str, Any], channel_names: AbstractSet[ChannelName]) -> Dict[str, Any]:
    """The stored document with every frame of the named channels written down to rests."""
    for stream in document[INSTRUCTIONS_DATA]:
        if stream[GENERATOR_NAME] in channel_names:
            for frame in stream[INSTRUCTIONS]:
                frame[INSTRUCTION][UNION_DATA][ON] = False

    return document


def _loaded_silenced(path: Path, channel_names: AbstractSet[ChannelName]) -> Reconstruction:
    """The archived file with the named channels resting through every frame, read with every rule held."""
    document = _silenced(stored_document(archived(ObjectKind.RECONSTRUCTION, RECONSTRUCTION_VERSION)), channel_names)
    path.write_bytes(msgpack.packb(document, use_bin_type=True))
    return Reconstruction.load(path, fast=False)


@pytest.fixture(name="silenced")
def silenced_fixture(tmp_path: Path) -> Reconstruction:
    """The archived file with its first pulse resting through every frame."""
    return _loaded_silenced(tmp_path / "silenced.stn", frozenset({SILENCED_CHANNEL}))


class TestAnArchivedChannelWrittenDownToRests:
    """A channel the last release stored resting through every frame reads as standing by."""

    def test_the_channel_stands_by(self, silenced: Reconstruction) -> None:
        assert SILENCED_CHANNEL not in silenced.playing_channels
        assert silenced.instructions[SILENCED_CHANNEL] == []

    def test_the_record_names_it_nowhere(self, silenced: Reconstruction) -> None:
        assert SILENCED_CHANNEL not in silenced.stems_data.assignments_by_channel

    def test_it_keeps_the_reference_it_stored(self, silenced: Reconstruction, validated: Reconstruction) -> None:
        assert silenced.initial_pitches[SILENCED_CHANNEL] == validated.initial_pitches[SILENCED_CHANNEL]
        assert silenced.held_features[SILENCED_CHANNEL] == validated.held_features[SILENCED_CHANNEL]

    def test_the_channels_beside_it_play_as_they_were_written(
        self,
        silenced: Reconstruction,
        validated: Reconstruction,
    ) -> None:
        for channel_name in validated.playing_channels:
            if channel_name != SILENCED_CHANNEL:
                assert silenced.instructions[channel_name] == validated.instructions[channel_name]


class TestAnArchivedFileSoundingNothing:
    """A file the last release stored resting on every channel keeps the recording it names."""

    @pytest.fixture(name="quiet")
    def quiet_fixture(self, tmp_path: Path) -> Reconstruction:
        return _loaded_silenced(tmp_path / "quiet.stn", frozenset(ChannelName.items()))

    def test_every_channel_stands_by(self, quiet: Reconstruction) -> None:
        assert quiet.playing_channels == ()

    def test_the_recording_stays_on_the_record(self, quiet: Reconstruction) -> None:
        assert [entry.id for entry in quiet.stems_data.config.entries] == [SINGLE_STEM_ID]
        assert quiet.audio_filepath == (SOURCE_PATH,)
