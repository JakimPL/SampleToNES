from __future__ import annotations

from typing import Callable

import pytest

from sampletones_application.logic.reconstruction.envelopes import heard_envelopes
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstruction.stems.source import StemSource
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.stems import STEM_A_ID, STEM_B_ID


@pytest.fixture
def reconstruction(
    reconstruction_factory: Callable[[], Reconstruction],
) -> Reconstruction:
    return reconstruction_factory()


@pytest.fixture
def everything_heard(reconstruction: Reconstruction) -> StemSelection:
    """The reader listening to every recording on every channel, as a fresh document reads."""
    return StemSelection.everywhere(
        frozenset(reconstruction.stems_data.config.entries_by_id),
        ChannelName.items(),
    )


@pytest.fixture
def envelopes(reconstruction: Reconstruction, everything_heard: StemSelection) -> ChannelEnvelopesViewModel:
    return heard_envelopes(reconstruction, everything_heard)


@pytest.fixture
def stems_reconstruction(reconstruction: Reconstruction) -> Reconstruction:
    """The same document read as two recordings, which is what gives a stretch something to name."""
    entries = [
        StemEntry(id=STEM_A_ID, settings=StemSettings.covering(list(reconstruction.playing_channels))),
        StemEntry(id=STEM_B_ID, settings=StemSettings.covering(list(reconstruction.playing_channels))),
    ]
    assignments = [
        ChannelAssignment(
            channel_name=channel_name,
            stem_ids=[
                STEM_A_ID if instruction.on and frame % 2 == 0 else STEM_B_ID if instruction.on else RESTING_STEM_ID
                for frame, instruction in enumerate(reconstruction.instructions[channel_name])
            ],
        )
        for channel_name in reconstruction.playing_channels
    ]
    reconstruction.stems_data = StemsData(
        config=StemsConfig(entries=entries, hierarchy=StemsHierarchy(levels=[[STEM_A_ID], [STEM_B_ID]])),
        sources=[
            StemSource(stem_id=STEM_A_ID, name="first", path=None),
            StemSource(stem_id=STEM_B_ID, name="second", path=None),
        ],
        assignments=assignments,
    )
    return reconstruction


@pytest.fixture
def everything_heard_of(stems_reconstruction: Reconstruction) -> StemSelection:
    return StemSelection.everywhere(
        frozenset(stems_reconstruction.stems_data.config.entries_by_id),
        ChannelName.items(),
    )


class TestTheEnvelopesOfWhatIsHeard:
    def test_every_generator_answers_with_an_entry(
        self,
        envelopes: ChannelEnvelopesViewModel,
    ) -> None:
        assert set(envelopes.channels.keys()) == set(ChannelName.items())

    def test_a_channel_standing_by_carries_empty_envelopes(
        self,
        reconstruction: Reconstruction,
        envelopes: ChannelEnvelopesViewModel,
    ) -> None:
        """A channel the reconstruction leaves silent is loaded describing no frame."""
        standing_by = set(ChannelName.items()) - set(reconstruction.playing_channels)
        assert standing_by
        assert all(not envelopes[channel_name].has_frames for channel_name in standing_by)

    def test_the_envelopes_state_the_pitch_they_are_measured_against(
        self,
        envelopes: ChannelEnvelopesViewModel,
    ) -> None:
        for features in envelopes.channels.values():
            assert features.initial_pitch is not None

    def test_hearing_every_recording_reads_the_document_itself(
        self,
        reconstruction: Reconstruction,
        envelopes: ChannelEnvelopesViewModel,
    ) -> None:
        """Each channel that sounds is read as the document writes it.

        A channel written down to rests alone stays in play, since every reader hears a rest.
        """
        whole = reconstruction.export()
        sounding = {name: features for name, features in whole.items() if features.has_frames}
        assert sounding

        assert {name: envelopes[name] for name in sounding} == sounding

    def test_a_channel_no_recording_is_heard_on_describes_no_frame(
        self,
        reconstruction: Reconstruction,
    ) -> None:
        playing = next(iter(reconstruction.playing_channels))

        envelopes = heard_envelopes(reconstruction, StemSelection(channels={}))

        assert not envelopes[playing].has_frames


class TestWhatTheEnvelopesAnswer:
    @pytest.mark.parametrize("channel_name", ChannelName.items(), ids=lambda name: name.value)
    def test_every_channel_answers_with_its_features(
        self,
        envelopes: ChannelEnvelopesViewModel,
        channel_name: ChannelName,
    ) -> None:
        assert isinstance(envelopes[channel_name], Features)


class TestTheRecordingsBehindWhatIsDrawn:
    """The stretches read the same frames the envelopes do, so a bar and its owner line up."""

    def test_a_document_answering_to_one_recording_tells_none_apart(
        self,
        envelopes: ChannelEnvelopesViewModel,
    ) -> None:
        assert envelopes.ownership == {}

    def test_every_sounding_channel_carries_its_stretches(
        self,
        stems_reconstruction: Reconstruction,
        everything_heard_of: StemSelection,
    ) -> None:
        envelopes = heard_envelopes(stems_reconstruction, everything_heard_of)

        sounding = {name for name, features in envelopes.channels.items() if features.has_frames}
        assert sounding
        assert set(envelopes.ownership) == sounding

    def test_a_channel_states_one_stretch_per_owner_it_changes_to(
        self,
        stems_reconstruction: Reconstruction,
        everything_heard_of: StemSelection,
    ) -> None:
        envelopes = heard_envelopes(stems_reconstruction, everything_heard_of)
        channel_name = next(iter(envelopes.ownership))
        owners = stems_reconstruction.stems_data.assignments_by_channel[channel_name]

        runs = envelopes.ownership[channel_name].runs

        assert [run.stem_id for run in runs] == [
            owner for index, owner in enumerate(owners) if index == 0 or owner != owners[index - 1]
        ]

    def test_the_stretches_stay_within_the_bars_they_stand_under(
        self,
        stems_reconstruction: Reconstruction,
        everything_heard_of: StemSelection,
    ) -> None:
        """A stretch names a frame the document records, and the bars may draw one more.

        An export releases the note it ends on, so a dimension's last item can stand past the
        frames the record holds; the stretches stop where the record does.
        """
        envelopes = heard_envelopes(stems_reconstruction, everything_heard_of)

        for channel_name, lane in envelopes.ownership.items():
            recorded = len(stems_reconstruction.stems_data.assignments_by_channel[channel_name])
            assert lane.runs[-1].end_frame == min(recorded, envelopes[channel_name].frame_count)
            assert lane.runs[0].start_frame == 0
