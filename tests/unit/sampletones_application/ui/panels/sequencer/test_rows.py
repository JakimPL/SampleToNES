import pytest

from sampletones_application.layout.loader import load_layout_config
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.layout.tabs.sequencer.colors.colors import SequencerColors
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
from sampletones_application.view_model.sequencer.settings import (
    SequencerSettingsViewModel,
)

NO_CUES = RowCues(cursor=None, playing=None)

PATTERN_ROWS = 64
BEAT_ROWS = 4
BAR_ROWS = 16


def _settings(
    *,
    first_highlight: int = BEAT_ROWS,
    second_highlight: int = BAR_ROWS,
) -> SequencerSettingsViewModel:
    """The module settings the row tinting reads, carrying the metre under test."""
    return SequencerSettingsViewModel(
        nes_frequency=60,
        tempo=150,
        speed=6,
        rows_per_pattern=PATTERN_ROWS,
        first_highlight=first_highlight,
        second_highlight=second_highlight,
    )


@pytest.fixture
def sequencer_layout() -> SequencerLayout:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source).tabs.sequencer


@pytest.fixture
def settings() -> SequencerSettingsViewModel:
    return _settings()


@pytest.fixture
def colors(sequencer_layout: SequencerLayout) -> SequencerColors:
    return sequencer_layout.colors


class TestGrouping:
    def test_the_row_opening_a_bar_takes_the_bar_shade(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        assert group_color(0, settings, colors) == colors.rows.bar
        assert group_color(settings.second_highlight, settings, colors) == colors.rows.bar

    def test_the_row_opening_a_beat_takes_the_beat_shade(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        beats = (
            settings.first_highlight,
            2 * settings.first_highlight,
            settings.second_highlight + settings.first_highlight,
        )

        for row_index in beats:
            assert group_color(row_index, settings, colors) == colors.rows.beat

    def test_a_row_inside_a_beat_keeps_its_stripe(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        for row_index in range(settings.rows_per_pattern):
            if row_index % settings.first_highlight != 0:
                assert group_color(row_index, settings, colors) is None

    def test_the_bar_shade_outranks_the_beat_shade_where_they_meet(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        """Every bar boundary opens a beat as well, and the row reads as the start of the bar."""
        assert settings.second_highlight % settings.first_highlight == 0
        assert group_color(settings.second_highlight, settings, colors) == colors.rows.bar

    def test_a_metre_the_project_states_moves_the_shades(
        self,
        colors: SequencerColors,
    ) -> None:
        """Three beats of four rows: the bar closes after twelve, where common time runs on to sixteen."""
        settings = _settings(first_highlight=4, second_highlight=12)

        assert group_color(12, settings, colors) == colors.rows.bar
        assert group_color(4, settings, colors) == colors.rows.beat
        assert group_color(8, settings, colors) == colors.rows.beat
        assert group_color(16, settings, colors) == colors.rows.beat
        assert group_color(3, settings, colors) is None

    def test_a_bar_shorter_than_a_beat_marks_every_bar_row(
        self,
        colors: SequencerColors,
    ) -> None:
        """The bar shade wins wherever the two groupings meet, so the shorter span is what shows."""
        settings = _settings(first_highlight=8, second_highlight=2)

        assert group_color(2, settings, colors) == colors.rows.bar
        assert group_color(8, settings, colors) == colors.rows.bar
        assert group_color(1, settings, colors) is None

    def test_a_highlight_of_one_marks_every_row(
        self,
        colors: SequencerColors,
    ) -> None:
        settings = _settings(first_highlight=1, second_highlight=1)

        for row_index in range(settings.rows_per_pattern):
            assert group_color(row_index, settings, colors) == colors.rows.bar


class TestCues:
    def test_the_playhead_outranks_the_cursor(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        cues = RowCues(cursor=5, playing=5)

        assert row_background(5, settings, colors, cues) == colors.playback_row

    def test_the_cursor_marks_the_row_it_rests_on(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        cues = RowCues(cursor=5, playing=9)

        assert row_background(5, settings, colors, cues) == colors.cursor_row

    def test_a_row_no_mark_stands_on_keeps_its_stripe(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        cues = RowCues(cursor=5, playing=9)

        assert row_background(6, settings, colors, cues) is None


class TestComposition:
    def test_a_marked_group_row_carries_the_cue_over_the_group_shade(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        row_index = settings.first_highlight
        cues = RowCues(cursor=row_index, playing=None)

        assert row_background(row_index, settings, colors, cues) == LayeredColor(
            base=colors.rows.beat,
            overlay=colors.cursor_row,
        )

    def test_the_composed_shade_covers_more_than_either_alone(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        row_index = settings.second_highlight
        cues = RowCues(cursor=None, playing=row_index)
        composed = row_background(row_index, settings, colors, cues)

        assert composed is not None
        assert composed.rgba[3] > max(colors.rows.bar.rgba[3], colors.playback_row.rgba[3])

    def test_an_unmarked_group_row_carries_the_group_shade_alone(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        assert row_background(0, settings, colors, NO_CUES) == colors.rows.bar
        assert row_background(settings.first_highlight, settings, colors, NO_CUES) == colors.rows.beat

    def test_a_plain_unmarked_row_leaves_the_layer_free(
        self,
        settings: SequencerSettingsViewModel,
        colors: SequencerColors,
    ) -> None:
        assert row_background(1, settings, colors, NO_CUES) is None
