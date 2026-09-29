from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, FrozenSet, List, Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.stems import RECORDED_SCALE

LEAD: Final[int] = 0
BASS: Final[int] = 1
RECORDINGS: Final[List[Path]] = [Path("/music/Lead.wav"), Path("/music/Bass.wav")]
EVERY_CHANNEL: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())
MEASURED_SCALE: Final[float] = 0.4


def _setup(stem_ids: Tuple[int, ...]) -> StemsConfig:
    channels = [ChannelName.PULSE1]
    return StemsConfig(
        entries=[
            StemEntry(id=stem_id, settings=StemSettings(channels=channels, bends=bending_channels(channels)))
            for stem_id in stem_ids
        ],
        hierarchy=StemsHierarchy(levels=[[stem_id] for stem_id in stem_ids]),
    )


def _record(stem_ids: List[int], *, scale: float = RECORDED_SCALE) -> StemsData:
    """Two recordings over the first pulse, whose frames ``stem_ids`` hands out."""
    return StemsData(
        config=_setup((LEAD, BASS)),
        assignments=[ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=stem_ids)],
        scale=scale,
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


class TestTheRecordedScale:
    """The factor a conversion read its recordings at belongs to the document, whatever it holds."""

    def test_a_record_stating_no_scale_holds_one_recording(self) -> None:
        record = StemsData(
            config=_setup((LEAD,)),
            assignments=[ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[LEAD])],
            scale=None,
        )

        assert record.scale is None

    def test_a_record_of_several_recordings_stating_no_scale_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            StemsData(
                config=_setup((LEAD, BASS)),
                assignments=[ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[LEAD, BASS])],
                scale=None,
            )


class TestTheScaleThroughEveryRewrite(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        rewrite: Callable[[StemsData], StemsData]

    test_cases: Tuple["TestTheScaleThroughEveryRewrite.TestCase", ...] = (
        TestCase(label="naming its sources", rewrite=lambda record: record.with_sources(RECORDINGS)),
        TestCase(label="detached", rewrite=lambda record: record.detached()),
        TestCase(
            label="given new owners",
            rewrite=lambda record: record.with_assignments(
                [ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[BASS, LEAD])]
            ),
        ),
        TestCase(label="letting an entry go", rewrite=lambda record: record.without_entries(frozenset({BASS}))),
        TestCase(label="settled", rewrite=lambda record: record.settled(EVERY_CHANNEL)),
        TestCase(label="settled with every channel standing by", rewrite=lambda record: record.settled(frozenset())),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_scale_survives(self, test_case: TestCase) -> None:
        assert test_case.rewrite(_record([LEAD, BASS], scale=MEASURED_SCALE)).scale == MEASURED_SCALE
