from pathlib import Path
from typing import Dict, Final, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, STEM_A_ID, taking_turns_reconstruction

SOURCES: Final[Tuple[Path, Path]] = (Path("a.wav"), Path("b.wav"))
EDITED: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=11, duty_cycle=1)
EDITED_PITCH: Final[int] = 67
RETUNED_RATE: Final[int] = 50


@pytest.fixture
def document() -> Reconstruction:
    """Two recordings taking turns on Pulse 1, the second holding Pulse 2 alone, its locations let go."""
    return taking_turns_reconstruction(SOURCES).detached()


def _streams(reconstruction: Reconstruction) -> Dict[ChannelName, InstructionsItem]:
    return {item.channel_name: item for item in reconstruction.instructions_data}


def _owners(reconstruction: Reconstruction) -> Dict[ChannelName, ChannelAssignment]:
    return {item.channel_name: item for item in reconstruction.stems_data.assignments}


class TestAnEditOwnsWhatItChanged:
    """An edit makes a new document that holds the very parts of the old one it left alone."""

    def test_a_channel_edit_shares_every_other_channel(self, document: Reconstruction) -> None:
        edited = document.with_channel_data(
            SHARED_CHANNEL,
            [EDITED, EDITED],
            EDITED_PITCH,
            (),
            heard=document.recorded_stem_ids,
        )

        assert edited is not document
        assert _streams(edited)[SOLE_CHANNEL] is _streams(document)[SOLE_CHANNEL]
        assert _owners(edited)[SOLE_CHANNEL] is _owners(document)[SOLE_CHANNEL]
        assert _streams(edited)[SHARED_CHANNEL] is not _streams(document)[SHARED_CHANNEL]

    def test_a_channel_edit_leaves_the_old_document_as_it_was(self, document: Reconstruction) -> None:
        before = list(document.instructions[SHARED_CHANNEL])

        document.with_channel_data(SHARED_CHANNEL, [EDITED, EDITED], EDITED_PITCH, (), heard=document.recorded_stem_ids)

        assert document.instructions[SHARED_CHANNEL] == before

    def test_a_removal_shares_the_channels_it_releases_nothing_from(self, document: Reconstruction) -> None:
        removed = without_stem(document, STEM_A_ID)

        assert _streams(removed)[SOLE_CHANNEL] is _streams(document)[SOLE_CHANNEL]
        assert _owners(removed)[SOLE_CHANNEL] is _owners(document)[SOLE_CHANNEL]
        assert _streams(removed)[SHARED_CHANNEL] is not _streams(document)[SHARED_CHANNEL]

    def test_a_retune_shares_every_stream_and_the_record(self, document: Reconstruction) -> None:
        retuned = document.with_nes_frequency(RETUNED_RATE)

        assert retuned.config.nes_frequency == RETUNED_RATE
        assert all(
            left is right for left, right in zip(retuned.instructions_data, document.instructions_data, strict=True)
        )
        assert retuned.stems_data is document.stems_data


class TestDetaching:
    """A document holding a location is detached into a new one sharing its streams; one holding none is kept."""

    def test_a_document_with_no_location_is_kept(self, document: Reconstruction) -> None:
        assert document.detached() is document

    def test_a_document_with_locations_detaches_into_a_new_one(self) -> None:
        located = taking_turns_reconstruction(SOURCES)

        detached = located.detached()

        assert detached is not located
        assert detached.audio_filepath == ()
        assert located.audio_filepath == SOURCES
        assert all(
            left is right for left, right in zip(detached.instructions_data, located.instructions_data, strict=True)
        )


class TestACopiedSample:
    """A duplicated sample shares its document until one of the two is edited."""

    def test_the_copy_holds_the_same_document(self, document: Reconstruction) -> None:
        original = Sample(name="Lead", reconstruction=document)

        copy = original.clone()

        assert copy.id != original.id
        assert copy.reconstruction is original.reconstruction
