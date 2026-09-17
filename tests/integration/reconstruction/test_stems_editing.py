from pathlib import Path
from typing import AbstractSet, Dict, Final, FrozenSet, List, Sequence

import numpy as np
import pytest

from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstruction.stems.filter import filter_approximations
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_tools.corpus.catalog import build_mini_library
from tests.suite.stems import (
    STEM_A_ID,
    STEM_B_ID,
    STEM_C_ID,
    THREE_STEM_CHANNELS,
    three_stem_config,
    three_stem_reconstruction_config,
    write_three_stem_recordings,
)

EVERY_STEM: Final[FrozenSet[int]] = frozenset({STEM_A_ID, STEM_B_ID, STEM_C_ID})
LOUDEST_VOLUME: Final[int] = 15
PITCH_STEP: Final[int] = 1


@pytest.fixture(scope="module")
def converted(tmp_path_factory: pytest.TempPathFactory) -> Reconstruction:
    """One real three-stem conversion, the document every scenario below starts from."""
    config = three_stem_reconstruction_config()
    library = build_mini_library(config)
    reconstructor = Reconstructor(config, frozenset(THREE_STEM_CHANNELS), library=library)
    paths = write_three_stem_recordings(config, tmp_path_factory.mktemp("recordings"))

    reconstruction = reconstructor.reconstruct(list(paths), three_stem_config())

    assert reconstruction is not None
    return reconstruction


@pytest.fixture
def reconstruction(converted: Reconstruction) -> Reconstruction:
    return converted.model_copy(deep=True)


def _owners(reconstruction: Reconstruction, channel_name: ChannelName) -> List[int]:
    return reconstruction.stems_data.assignments_by_channel[channel_name]


def _holders(reconstruction: Reconstruction, channel_name: ChannelName) -> List[int]:
    """The recordings holding a frame of this channel, in id order."""
    return sorted(set(_owners(reconstruction, channel_name)) - {RESTING_STEM_ID, AUTHORED_STEM_ID})


def _contested_channel(reconstruction: Reconstruction) -> ChannelName:
    """A channel two recordings share, which is where an edit's scope is worth asking about."""
    for channel_name in reconstruction.playing_channels:
        if len(_holders(reconstruction, channel_name)) > 1:
            return channel_name

    raise AssertionError("The conversion gave no channel to two recordings")


def _channel_with_a_rest(reconstruction: Reconstruction) -> ChannelName:
    """A channel holding both a recording's frame and a resting one, where writing into silence reaches."""
    for channel_name in reconstruction.playing_channels:
        owners = _owners(reconstruction, channel_name)
        if RESTING_STEM_ID in owners and _holders(reconstruction, channel_name):
            return channel_name

    raise AssertionError("The conversion left no channel holding both a recording and a rest")


def _frames_of(reconstruction: Reconstruction, channel_name: ChannelName, stem_id: int) -> List[int]:
    return [frame for frame, held in enumerate(_owners(reconstruction, channel_name)) if held == stem_id]


def _edited(
    reconstruction: Reconstruction,
    channel_name: ChannelName,
    instructions: Sequence[InstructionUnion],
    *,
    heard: AbstractSet[int] = EVERY_STEM,
) -> Reconstruction:
    edited = reconstruction.model_copy(deep=True)
    edited.update_channel_data(
        channel_name,
        list(instructions),
        initial_pitch=reconstruction.initial_pitches[channel_name],
        held_features=reconstruction.held_features[channel_name],
        heard=heard,
    )
    return edited


def _changed(instruction: InstructionUnion) -> InstructionUnion:
    """The same frame sounding differently, whichever dimensions its channel reads.

    A silent frame comes back as it stands, so a stream reshaped through this keeps resting
    where it rested and states the reader's change everywhere it sounds.
    """
    if not instruction.on:
        return instruction

    match instruction:
        case TriangleInstruction():
            return instruction.model_copy(update={"pitch": instruction.pitch + PITCH_STEP})
        case _:
            return instruction.model_copy(update={"volume": LOUDEST_VOLUME})


def _changed_stream(reconstruction: Reconstruction, channel_name: ChannelName) -> List[InstructionUnion]:
    return [_changed(instruction) for instruction in reconstruction.instructions[channel_name]]


def _stream_with(
    reconstruction: Reconstruction,
    channel_name: ChannelName,
    changes: Dict[int, InstructionUnion],
) -> List[InstructionUnion]:
    return [
        changes.get(frame, instruction) for frame, instruction in enumerate(reconstruction.instructions[channel_name])
    ]


def _first_sounding(reconstruction: Reconstruction, channel_name: ChannelName) -> InstructionUnion:
    return next(instruction for instruction in reconstruction.instructions[channel_name] if instruction.on)


class TestAnEditOnAFrameARecordingHolds:
    def test_every_frame_keeps_the_recording_that_held_it(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        before = _owners(reconstruction, channel_name)

        edited = _edited(reconstruction, channel_name, _changed_stream(reconstruction, channel_name))

        assert _owners(edited, channel_name) == before

    def test_the_edit_reaches_the_frames_it_names(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        proposed = _changed_stream(reconstruction, channel_name)

        edited = _edited(reconstruction, channel_name, proposed)

        assert edited.instructions[channel_name] == proposed

    def test_the_setup_and_the_sources_stand_as_they_did(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)

        edited = _edited(reconstruction, channel_name, _changed_stream(reconstruction, channel_name))

        assert edited.stems_data.config == reconstruction.stems_data.config
        assert edited.audio_filepath == reconstruction.audio_filepath
        assert edited.coefficient == reconstruction.coefficient

    def test_the_channels_beside_it_are_left_alone(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        before = dict(reconstruction.stems_data.assignments_by_channel)

        edited = _edited(reconstruction, channel_name, _changed_stream(reconstruction, channel_name))

        for name, stem_ids in edited.stems_data.assignments_by_channel.items():
            if name != channel_name:
                assert stem_ids == before[name]


class TestAnEditOutsideWhatIsHeard:
    def test_a_frame_of_a_recording_left_out_stands_as_it_is(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        unheard = _holders(reconstruction, channel_name)[0]
        before = list(reconstruction.instructions[channel_name])

        edited = _edited(
            reconstruction,
            channel_name,
            _changed_stream(reconstruction, channel_name),
            heard=EVERY_STEM - {unheard},
        )

        for frame in _frames_of(reconstruction, channel_name, unheard):
            assert edited.instructions[channel_name][frame] == before[frame]
            assert _owners(edited, channel_name)[frame] == unheard

    def test_the_recordings_the_reader_hears_take_the_edit(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        holders = _holders(reconstruction, channel_name)
        heard = frozenset(holders[1:])
        proposed = _changed_stream(reconstruction, channel_name)

        edited = _edited(reconstruction, channel_name, proposed, heard=heard)

        for stem_id in heard:
            for frame in _frames_of(reconstruction, channel_name, stem_id):
                assert edited.instructions[channel_name][frame] == proposed[frame]
                assert _owners(edited, channel_name)[frame] == stem_id


class TestAnEditThatChangesWhoSounds:
    def test_a_resting_frame_written_into_play_is_the_readers_own(self, reconstruction: Reconstruction) -> None:
        channel_name = _channel_with_a_rest(reconstruction)
        frame = _frames_of(reconstruction, channel_name, RESTING_STEM_ID)[0]
        proposed = _stream_with(reconstruction, channel_name, {frame: _first_sounding(reconstruction, channel_name)})

        edited = _edited(reconstruction, channel_name, proposed)

        assert _owners(edited, channel_name)[frame] == AUTHORED_STEM_ID
        assert edited.instructions[channel_name][frame].on

    def test_the_frames_beside_it_keep_their_recordings(self, reconstruction: Reconstruction) -> None:
        channel_name = _channel_with_a_rest(reconstruction)
        frame = _frames_of(reconstruction, channel_name, RESTING_STEM_ID)[0]
        before = _owners(reconstruction, channel_name)
        proposed = _stream_with(reconstruction, channel_name, {frame: _first_sounding(reconstruction, channel_name)})

        edited = _edited(reconstruction, channel_name, proposed)

        after = _owners(edited, channel_name)
        assert [owner for index, owner in enumerate(after) if index != frame] == [
            owner for index, owner in enumerate(before) if index != frame
        ]

    def test_a_held_frame_quieted_rests(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        held = _holders(reconstruction, channel_name)[0]
        frame = _frames_of(reconstruction, channel_name, held)[0]
        silence = type(reconstruction.instructions[channel_name][frame]).null_instruction()

        edited = _edited(reconstruction, channel_name, _stream_with(reconstruction, channel_name, {frame: silence}))

        assert _owners(edited, channel_name)[frame] == RESTING_STEM_ID
        assert not edited.instructions[channel_name][frame].on


class TestAChannelAnEditEmpties:
    def test_the_channel_stands_by_and_leaves_the_record(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)

        edited = _edited(reconstruction, channel_name, [])

        assert channel_name not in edited.playing_channels
        assert channel_name not in edited.stems_data.assignments_by_channel
        assert channel_name not in edited.approximations

    def test_the_recordings_stay_on_the_record(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)

        edited = _edited(reconstruction, channel_name, [])

        assert edited.stems_data.config == reconstruction.stems_data.config
        assert edited.audio_filepath == reconstruction.audio_filepath

    def test_writing_it_back_into_play_makes_it_the_readers_own(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        stream = [_first_sounding(reconstruction, channel_name)] * 3

        edited = _edited(_edited(reconstruction, channel_name, []), channel_name, stream)

        assert _owners(edited, channel_name) == [AUTHORED_STEM_ID] * len(stream)


class TestARecordingTakenOutAfterAnEdit:
    def test_the_frames_it_held_are_released_all_the_same(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        removed = _holders(reconstruction, channel_name)[0]
        frames = _frames_of(reconstruction, channel_name, removed)
        edited = _edited(reconstruction, channel_name, _changed_stream(reconstruction, channel_name))

        remaining = without_stem(edited, removed)

        assert removed not in remaining.stems_data.config.entries_by_id
        for frame in frames:
            assert _owners(remaining, channel_name)[frame] == RESTING_STEM_ID
            assert not remaining.instructions[channel_name][frame].on

    def test_the_frames_the_reader_wrote_stand_through_the_removal(self, reconstruction: Reconstruction) -> None:
        channel_name = _channel_with_a_rest(reconstruction)
        frame = _frames_of(reconstruction, channel_name, RESTING_STEM_ID)[0]
        removed = _holders(reconstruction, channel_name)[0]
        proposed = _stream_with(reconstruction, channel_name, {frame: _first_sounding(reconstruction, channel_name)})
        edited = _edited(reconstruction, channel_name, proposed)

        remaining = without_stem(edited, removed)

        assert _owners(remaining, channel_name)[frame] == AUTHORED_STEM_ID
        assert remaining.instructions[channel_name][frame].on

    def test_the_recordings_that_stay_keep_their_frames(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        holders = _holders(reconstruction, channel_name)
        removed, kept = holders[0], holders[1]
        edited = _edited(reconstruction, channel_name, _changed_stream(reconstruction, channel_name))

        remaining = without_stem(edited, removed)

        for frame in _frames_of(reconstruction, channel_name, kept):
            assert _owners(remaining, channel_name)[frame] == kept
            assert remaining.instructions[channel_name][frame] == edited.instructions[channel_name][frame]


class TestADetachedDocument:
    def test_it_keeps_every_recording_it_was_built_from(self, reconstruction: Reconstruction) -> None:
        detached = reconstruction.model_copy(deep=True)

        detached.detach_source()

        assert detached.audio_filepath == ()
        assert detached.stems_data.assignments_by_channel == reconstruction.stems_data.assignments_by_channel
        assert [entry.id for entry in detached.stems_data.config.entries] == [
            entry.id for entry in reconstruction.stems_data.config.entries
        ]

    def test_it_edits_the_way_an_attached_one_does(self, reconstruction: Reconstruction) -> None:
        channel_name = _contested_channel(reconstruction)
        detached = reconstruction.model_copy(deep=True)
        detached.detach_source()

        edited = _edited(detached, channel_name, _changed_stream(detached, channel_name))

        assert _owners(edited, channel_name) == _owners(reconstruction, channel_name)


class TestWhatASelectionLeaves:
    def test_a_recording_heard_alone_keeps_its_own_frames_and_quiets_the_rest(
        self,
        reconstruction: Reconstruction,
    ) -> None:
        channel_name = _contested_channel(reconstruction)
        held = _holders(reconstruction, channel_name)[0]
        frame_length = reconstruction.config.library.frame_length
        selection = StemSelection(channels={channel_name: frozenset({held})})

        filtered = filter_approximations(
            reconstruction.stems_data,
            reconstruction.approximations,
            selection,
            frame_length,
        )

        for frame, owner in enumerate(_owners(reconstruction, channel_name)):
            window = slice(frame * frame_length, (frame + 1) * frame_length)
            expected = (
                reconstruction.approximations[channel_name][window]
                if owner == held
                else np.zeros(frame_length, dtype=filtered[channel_name].dtype)
            )
            np.testing.assert_array_equal(filtered[channel_name][window], expected)


class TestTheDocumentThroughAFile:
    def test_an_edited_document_round_trips_whole(self, reconstruction: Reconstruction, tmp_path: Path) -> None:
        channel_name = _contested_channel(reconstruction)
        edited = _edited(reconstruction, channel_name, _changed_stream(reconstruction, channel_name))
        path = tmp_path / "edited.stn"

        edited.save(path)
        restored = Reconstruction.load(path)

        assert restored.stems_data.assignments_by_channel == edited.stems_data.assignments_by_channel
        assert restored.stems_data.config == edited.stems_data.config
        for name in edited.playing_channels:
            np.testing.assert_array_equal(restored.approximations[name], edited.approximations[name])
