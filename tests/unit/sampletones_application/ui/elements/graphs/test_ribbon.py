from typing import Final, List, Tuple

import pytest

from sampletones_application.layout.general.colors.stem import StemColors
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_application.view_model.shared.ownership import (
    OwnershipLaneViewModel,
    OwnershipRibbonViewModel,
    OwnershipRunViewModel,
)
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import ColorRGBA

RECORDING_COLORS: Final[Tuple[ColorRGBA, ...]] = (
    (200, 80, 40, 255),
    (80, 160, 220, 255),
    (120, 200, 130, 255),
)
AUTHORED_COLOR: Final[ColorRGBA] = (180, 140, 240, 255)
REST_COLOR: Final[ColorRGBA] = (40, 40, 48, 255)
FRAME_LENGTH: Final[int] = 4


@pytest.fixture
def stem_colors() -> StemColors:
    return StemColors(
        recordings=tuple(LiteralColor(value) for value in RECORDING_COLORS),
        authored=LiteralColor(AUTHORED_COLOR),
        rest=LiteralColor(REST_COLOR),
    )


def _runs(*entries: Tuple[int, int, int, int]) -> Tuple[OwnershipRunViewModel, ...]:
    return tuple(
        OwnershipRunViewModel(start_frame=start, end_frame=end, stem_id=stem_id, position=position)
        for start, end, stem_id, position in entries
    )


class TestTheColorARecordingIsKnownBy:
    def test_a_recording_takes_the_color_of_the_place_it_holds(self, stem_colors: StemColors) -> None:
        assert stem_colors.for_stem(7, 1).rgba == LiteralColor(RECORDING_COLORS[1]).rgba

    def test_the_list_starts_over_for_a_document_holding_more_recordings(
        self,
        stem_colors: StemColors,
    ) -> None:
        assert stem_colors.for_position(len(RECORDING_COLORS)).rgba == stem_colors.for_position(0).rgba

    def test_the_frames_the_reader_wrote_take_a_color_of_their_own(self, stem_colors: StemColors) -> None:
        assert stem_colors.for_stem(AUTHORED_STEM_ID, 0).rgba == LiteralColor(AUTHORED_COLOR).rgba

    def test_a_resting_frame_shows_the_ground(self, stem_colors: StemColors) -> None:
        assert stem_colors.for_stem(RESTING_STEM_ID, 0).rgba == LiteralColor(REST_COLOR).rgba


class TestWhatTheRibbonStandsFor:
    @staticmethod
    def _ribbon(lanes: List[OwnershipLaneViewModel], total_frames: int) -> OwnershipRibbonViewModel:
        return OwnershipRibbonViewModel(
            lanes=tuple(lanes),
            frame_length=FRAME_LENGTH,
            total_frames=total_frames,
        )

    def test_a_ribbon_with_lanes_is_drawn(self) -> None:
        lane = OwnershipLaneViewModel(channel_name=ChannelName.PULSE1, runs=_runs((0, 4, 0, 0)))

        assert self._ribbon([lane], 4).is_drawn

    def test_a_ribbon_with_no_lane_stands_down(self) -> None:
        assert not self._ribbon([], 4).is_drawn

    def test_a_ribbon_covering_no_frame_stands_down(self) -> None:
        lane = OwnershipLaneViewModel(channel_name=ChannelName.PULSE1, runs=())

        assert not self._ribbon([lane], 0).is_drawn

    def test_the_span_it_covers_is_stated_in_the_samples_the_waveform_counts(self) -> None:
        lane = OwnershipLaneViewModel(channel_name=ChannelName.PULSE1, runs=_runs((0, 6, 0, 0)))

        assert self._ribbon([lane], 6).total_samples == 6 * FRAME_LENGTH

    def test_an_empty_ribbon_stands_for_nothing(self) -> None:
        empty = OwnershipRibbonViewModel.empty()

        assert not empty.is_drawn
        assert empty.total_samples == 0
