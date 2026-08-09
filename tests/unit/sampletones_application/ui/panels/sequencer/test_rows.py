import pytest

from sampletones_application.layout.loader import load_layout_config
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.layout.tabs.sequencer.colors.colors import SequencerColors
from sampletones_application.layout.tabs.sequencer.tracker.tracker import TrackerLayout
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
)
from sampletones_application.ui.panels.sequencer.rows import (
    RowCues,
    group_color,
    row_background,
)
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.colors.layered import LayeredColor
from sampletones_application.utils.palette.source import PaletteSource

NO_CUES = RowCues(cursor=None, playing=None)


@pytest.fixture
def sequencer_layout() -> SequencerLayout:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source).tabs.sequencer


@pytest.fixture
def tracker(sequencer_layout: SequencerLayout) -> TrackerLayout:
    return sequencer_layout.tracker


@pytest.fixture
def colors(sequencer_layout: SequencerLayout) -> SequencerColors:
    return sequencer_layout.colors


class TestGrouping:
    def test_the_row_opening_a_bar_takes_the_bar_shade(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        assert group_color(0, tracker, colors) == colors.rows.bar
        assert group_color(tracker.rows_per_bar, tracker, colors) == colors.rows.bar

    def test_the_row_opening_a_beat_takes_the_beat_shade(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        beats = (
            tracker.rows_per_beat,
            2 * tracker.rows_per_beat,
            tracker.rows_per_bar + tracker.rows_per_beat,
        )

        for row_index in beats:
            assert group_color(row_index, tracker, colors) == colors.rows.beat

    def test_a_row_inside_a_beat_keeps_its_stripe(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        for row_index in range(tracker.rows):
            if row_index % tracker.rows_per_beat != 0:
                assert group_color(row_index, tracker, colors) is None

    def test_the_bar_shade_outranks_the_beat_shade_where_they_meet(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        """Every bar boundary opens a beat as well, and the row reads as the start of the bar."""
        assert tracker.rows_per_bar % tracker.rows_per_beat == 0
        assert group_color(tracker.rows_per_bar, tracker, colors) == colors.rows.bar

    def test_grouping_counts_of_zero_leave_every_row_even(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        flat = tracker.model_copy(update={"rows_per_beat": 0, "rows_per_bar": 0})

        for row_index in range(tracker.rows):
            assert group_color(row_index, flat, colors) is None


class TestCues:
    def test_the_playhead_outranks_the_cursor(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        cues = RowCues(cursor=5, playing=5)

        assert row_background(5, tracker, colors, cues) == colors.playback_row

    def test_the_cursor_marks_the_row_it_rests_on(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        cues = RowCues(cursor=5, playing=9)

        assert row_background(5, tracker, colors, cues) == colors.cursor_row

    def test_a_row_no_mark_stands_on_keeps_its_stripe(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        cues = RowCues(cursor=5, playing=9)

        assert row_background(6, tracker, colors, cues) is None


class TestComposition:
    def test_a_marked_group_row_carries_the_cue_over_the_group_shade(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        row_index = tracker.rows_per_beat
        cues = RowCues(cursor=row_index, playing=None)

        assert row_background(row_index, tracker, colors, cues) == LayeredColor(
            base=colors.rows.beat,
            overlay=colors.cursor_row,
        )

    def test_the_composed_shade_covers_more_than_either_alone(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        row_index = tracker.rows_per_bar
        cues = RowCues(cursor=None, playing=row_index)
        composed = row_background(row_index, tracker, colors, cues)

        assert composed is not None
        assert composed.rgba[3] > max(colors.rows.bar.rgba[3], colors.playback_row.rgba[3])

    def test_an_unmarked_group_row_carries_the_group_shade_alone(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        assert row_background(0, tracker, colors, NO_CUES) == colors.rows.bar
        assert row_background(tracker.rows_per_beat, tracker, colors, NO_CUES) == colors.rows.beat

    def test_a_plain_unmarked_row_leaves_the_layer_free(
        self,
        tracker: TrackerLayout,
        colors: SequencerColors,
    ) -> None:
        assert row_background(1, tracker, colors, NO_CUES) is None
