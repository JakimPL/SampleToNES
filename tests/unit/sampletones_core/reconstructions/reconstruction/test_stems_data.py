from pathlib import Path
from typing import Final, FrozenSet, List

from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

LEAD: Final[int] = 0
BASS: Final[int] = 1
RECORDINGS: Final[List[Path]] = [Path("/music/Lead.wav"), Path("/music/Bass.wav")]
EVERY_CHANNEL: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())


def _record(stem_ids: List[int]) -> StemsData:
    """Two recordings over the first pulse, whose frames ``stem_ids`` hands out."""
    channels = [ChannelName.PULSE1]
    return StemsData(
        config=StemsConfig(
            entries=[
                StemEntry(id=stem_id, settings=StemSettings(channels=channels, bends=bending_channels(channels)))
                for stem_id in (LEAD, BASS)
            ],
            hierarchy=StemsHierarchy(levels=[[LEAD], [BASS]]),
        ),
        assignments=[ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=stem_ids)],
    ).with_sources(RECORDINGS)


class TestTheRecordingsHoldingAFrame:
    def test_every_recording_named_in_a_frame_holds_one(self) -> None:
        assert _record([LEAD, BASS]).holding_stem_ids == frozenset({LEAD, BASS})

    def test_a_rest_and_the_readers_own_frames_hold_for_no_recording(self) -> None:
        assert _record([LEAD, RESTING_STEM_ID, AUTHORED_STEM_ID]).holding_stem_ids == frozenset({LEAD})


class TestWhatSettlingLetsGoOf:
    """A settled record names the recordings behind its frames, unless nothing tells them apart."""

    def test_a_recording_holding_no_frame_leaves_with_its_source(self) -> None:
        settled = _record([LEAD, RESTING_STEM_ID]).settled(EVERY_CHANNEL)

        assert [entry.id for entry in settled.config.entries] == [LEAD]
        assert [source.stem_id for source in settled.sources] == [LEAD]
        assert settled.config.hierarchy.levels == [[LEAD]]
        assert settled.paths == (RECORDINGS[0],)

    def test_a_record_where_no_recording_holds_a_frame_keeps_them_all(self) -> None:
        settled = _record([RESTING_STEM_ID, RESTING_STEM_ID]).settled(EVERY_CHANNEL)

        assert [entry.id for entry in settled.config.entries] == [LEAD, BASS]
        assert settled.paths == tuple(RECORDINGS)

    def test_authored_frames_alone_keep_every_recording(self) -> None:
        settled = _record([AUTHORED_STEM_ID, RESTING_STEM_ID]).settled(EVERY_CHANNEL)

        assert [entry.id for entry in settled.config.entries] == [LEAD, BASS]

    def test_a_record_whose_channels_all_stand_by_keeps_every_recording(self) -> None:
        settled = _record([LEAD, BASS]).settled(frozenset())

        assert settled.assignments == []
        assert [entry.id for entry in settled.config.entries] == [LEAD, BASS]

    def test_a_record_every_recording_holds_a_frame_in_stands_whole(self) -> None:
        record = _record([BASS, LEAD])

        assert record.settled(EVERY_CHANNEL) == record
