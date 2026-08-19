from types import SimpleNamespace
from typing import Dict, FrozenSet, List, Optional, Tuple

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.tabs.sequencer.colors.channel import ChannelColors
from sampletones_application.paths import LANG_EN
from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer import channels as channels_module
from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.columns import tracker_table_column
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.modifiers import (
    CTRL,
    NO_MODIFIERS,
    ModifierSet,
)
from sampletones_application.utils.palette.colors.written import LiteralColor
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import ColorRGBA, Sender

HEADER_WIDGET_ID = 7100
"""A stand-in for the header selectable id DearPyGui passes as the callback's sender."""

ROW_COUNT = 3
TINT_FRACTION = 0.5
MUTED_TEXT_FRACTION = 0.25

MUTED_BACKGROUND: ColorRGBA = (10, 8, 18, 96)
CHANNEL_COLORS = ChannelColors(
    pulse1=LiteralColor((240, 146, 86, 255)),
    pulse2=LiteralColor((242, 209, 95, 255)),
    triangle=LiteralColor((140, 193, 237, 255)),
    noise=LiteralColor((187, 184, 194, 255)),
)

HEADER_THEME = 1
MUTED_HEADER_THEME = 2
SUBCOLUMN_THEMES: Dict[SubColumn, int] = {
    SubColumn.INSTRUMENT: 10,
    SubColumn.TRANSPOSE: 11,
    SubColumn.VOLUME: 12,
}
MUTED_SUBCOLUMN_THEMES: Dict[SubColumn, int] = {
    SubColumn.INSTRUMENT: 20,
    SubColumn.TRANSPOSE: 21,
    SubColumn.VOLUME: 22,
}


class _DearPyGuiRecorder:
    """Captures the DearPyGui calls the channel cues make, standing in for a live table."""

    def __init__(self, *, table_exists: bool = True) -> None:
        self.table_exists = table_exists
        self.column_tints: Dict[int, ColorRGBA] = {}
        self.bound_themes: Dict[Sender, int] = {}
        self.released: List[Sender] = []

    def does_item_exist(self, item: Sender) -> bool:
        return self.table_exists

    def highlight_table_column(self, table: str, column: int, color: ColorRGBA) -> None:
        self.column_tints[column] = color

    def bind_item_theme(self, item: Sender, theme: int) -> None:
        self.bound_themes[item] = theme

    def set_value(self, item: Sender, value: bool) -> None:
        self.released.append(item)


HEADER_COLUMNS: Tuple[Optional[ChannelName], ...] = (None, *ChannelName.items())


def _header_widget(channel: Optional[ChannelName]) -> int:
    """A stable stand-in widget id per header column."""
    return 100 + HEADER_COLUMNS.index(channel)


def _cell_widget(channel: ChannelName, row_index: int, subcolumn: SubColumn) -> int:
    return 1000 + 100 * ChannelName.items().index(channel) + 10 * row_index + list(SubColumn).index(subcolumn)


def _panel(muted: FrozenSet[ChannelName]) -> GUISequencerTrackerPanel:
    """Builds a panel around the state the channel cues read, with no DearPyGui context.

    The cues touch the layout colours, the theme ids, the header widgets, and the cell
    registry, so those are wired directly and the rest of the panel is left out.
    """
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._layout = SimpleNamespace(
        colors=SimpleNamespace(
            channels=CHANNEL_COLORS,
            muted=SimpleNamespace(background=LiteralColor(MUTED_BACKGROUND)),
        ),
        tracker=SimpleNamespace(
            channel_column_tint=TINT_FRACTION,
            muted_text_fraction=MUTED_TEXT_FRACTION,
        ),
    )
    panel._current_channels = SequencerChannelsViewModel(muted=muted)
    panel._current_row_count = ROW_COUNT
    panel._header_theme = HEADER_THEME
    panel._muted_header_theme = MUTED_HEADER_THEME
    panel._subcolumn_themes = dict(SUBCOLUMN_THEMES)
    panel._muted_subcolumn_themes = dict(MUTED_SUBCOLUMN_THEMES)
    panel._header_columns = {_header_widget(channel): channel for channel in HEADER_COLUMNS}
    panel._create_channel_switch(LanguageManager(LANG_EN))
    panel._editable_cells = EditableCells()
    for channel in ChannelName.items():
        for row_index in range(ROW_COUNT):
            for subcolumn in SubColumn:
                panel._editable_cells.register(
                    (row_index, channel, subcolumn),
                    _cell_widget(channel, row_index, subcolumn),
                )

    return panel


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _DearPyGuiRecorder:
    instance = _DearPyGuiRecorder()
    monkeypatch.setattr(tracker_module.dpg, "does_item_exist", instance.does_item_exist)
    monkeypatch.setattr(tracker_module.dpg, "highlight_table_column", instance.highlight_table_column)
    monkeypatch.setattr(tracker_module.dpg, "bind_item_theme", instance.bind_item_theme)
    monkeypatch.setattr(tracker_module.dpg, "set_value", instance.set_value)
    return instance


def _hold(monkeypatch: pytest.MonkeyPatch, modifiers: ModifierSet) -> None:
    monkeypatch.setattr(channels_module, "capture_modifiers", lambda: modifiers)


class TestHeaderClickDispatch:
    def test_plain_click_toggles_the_clicked_channel(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, NO_MODIFIERS)
        toggled: List[ChannelName] = []
        panel.on_channel_mute_toggled = toggled.append

        panel._on_header_clicked(HEADER_WIDGET_ID, True, ChannelName.TRIANGLE)

        assert toggled == [ChannelName.TRIANGLE]

    def test_ctrl_click_solos_the_clicked_channel(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, CTRL)
        soloed: List[ChannelName] = []
        panel.on_channel_soloed = soloed.append
        panel.on_channel_mute_toggled = lambda _: pytest.fail("Ctrl+click must not toggle")

        panel._on_header_clicked(HEADER_WIDGET_ID, True, ChannelName.NOISE)

        assert soloed == [ChannelName.NOISE]

    def test_sample_header_switches_every_channel(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, NO_MODIFIERS)
        switches: List[None] = []
        panel.on_channels_toggled = lambda: switches.append(None)
        panel.on_channel_mute_toggled = lambda _: pytest.fail("the sample header addresses no single channel")

        panel._on_header_clicked(HEADER_WIDGET_ID, True, None)

        assert switches == [None]

    def test_ctrl_on_the_sample_header_still_switches_every_channel(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, CTRL)
        switches: List[None] = []
        panel.on_channels_toggled = lambda: switches.append(None)
        panel.on_channel_soloed = lambda _: pytest.fail("the sample header addresses no single channel")

        panel._on_header_clicked(HEADER_WIDGET_ID, True, None)

        assert switches == [None]

    @pytest.mark.parametrize(
        "channel",
        HEADER_COLUMNS,
        ids=lambda channel: "sample" if channel is None else channel.value,
    )
    def test_every_header_click_releases_the_selectable(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
        channel: Optional[ChannelName],
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, NO_MODIFIERS)
        panel.on_channels_toggled = lambda: None
        panel.on_channel_mute_toggled = lambda _: None

        panel._on_header_clicked(HEADER_WIDGET_ID, True, channel)

        assert recorder.released == [HEADER_WIDGET_ID]


class TestColumnWash:
    def test_audible_channel_keeps_its_identity_tint(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset())

        panel._apply_channel_cues()

        column = tracker_table_column(ChannelName.PULSE1)
        assert recorder.column_tints[column] == (240, 146, 86, 128)

    def test_muted_channel_takes_the_neutral_wash(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({ChannelName.PULSE1}))

        panel._apply_channel_cues()

        column = tracker_table_column(ChannelName.PULSE1)
        assert recorder.column_tints[column] == MUTED_BACKGROUND

    def test_the_other_channels_keep_their_tint_while_one_is_muted(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({ChannelName.TRIANGLE}))

        panel._apply_channel_cues()

        washed = {
            channel
            for channel in ChannelName.items()
            if recorder.column_tints[tracker_table_column(channel)] == MUTED_BACKGROUND
        }
        assert washed == {ChannelName.TRIANGLE}

    def test_every_channel_column_is_painted(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset())

        panel._apply_channel_cues()

        expected = {tracker_table_column(channel) for channel in ChannelName.items()}
        assert expected <= set(recorder.column_tints)


class TestHeaderLabelShade:
    def test_muted_channel_label_takes_the_muted_shade(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({ChannelName.PULSE2}))

        panel._apply_channel_cues()

        assert recorder.bound_themes[_header_widget(ChannelName.PULSE2)] == MUTED_HEADER_THEME

    def test_audible_channel_label_keeps_the_plain_shade(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({ChannelName.PULSE2}))

        panel._apply_channel_cues()

        assert recorder.bound_themes[_header_widget(ChannelName.NOISE)] == HEADER_THEME

    def test_sample_label_keeps_the_plain_shade_with_every_channel_muted(
        self,
        recorder: _DearPyGuiRecorder,
    ) -> None:
        panel = _panel(frozenset(ChannelName.items()))

        panel._apply_channel_cues()

        assert recorder.bound_themes[_header_widget(None)] == HEADER_THEME


class TestCellTextShade:
    def test_muted_channel_cells_take_the_dimmed_theme(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({ChannelName.TRIANGLE}))

        panel._apply_channel_cues()

        bound = {
            recorder.bound_themes[_cell_widget(ChannelName.TRIANGLE, row_index, subcolumn)]
            for row_index in range(ROW_COUNT)
            for subcolumn in SubColumn
        }
        assert bound == set(MUTED_SUBCOLUMN_THEMES.values())

    def test_audible_channel_cells_take_the_full_theme(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({ChannelName.TRIANGLE}))

        panel._apply_channel_cues()

        bound = {
            recorder.bound_themes[_cell_widget(ChannelName.PULSE1, row_index, subcolumn)]
            for row_index in range(ROW_COUNT)
            for subcolumn in SubColumn
        }
        assert bound == set(SUBCOLUMN_THEMES.values())

    def test_each_subcolumn_keeps_its_own_hue_when_dimmed(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({ChannelName.NOISE}))

        panel._apply_channel_cues()

        for subcolumn in SubColumn:
            widget = _cell_widget(ChannelName.NOISE, 0, subcolumn)
            assert recorder.bound_themes[widget] == MUTED_SUBCOLUMN_THEMES[subcolumn]

    def test_unmuting_restores_the_full_theme(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({ChannelName.NOISE}))
        panel._apply_channel_cues()

        panel.update_channels(SequencerChannelsViewModel(muted=frozenset()))

        widget = _cell_widget(ChannelName.NOISE, 1, SubColumn.VOLUME)
        assert recorder.bound_themes[widget] == SUBCOLUMN_THEMES[SubColumn.VOLUME]


class TestCuesAwaitTheTable:
    def test_the_model_is_kept_while_the_table_is_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A mute set pushed before the table exists is reapplied by the next rebuild."""
        instance = _DearPyGuiRecorder(table_exists=False)
        monkeypatch.setattr(tracker_module.dpg, "does_item_exist", instance.does_item_exist)
        monkeypatch.setattr(
            tracker_module.dpg,
            "highlight_table_column",
            instance.highlight_table_column,
        )
        monkeypatch.setattr(tracker_module.dpg, "bind_item_theme", instance.bind_item_theme)
        panel = _panel(frozenset())

        panel.update_channels(SequencerChannelsViewModel(muted=frozenset({ChannelName.PULSE1})))

        assert not instance.column_tints
        assert not instance.bound_themes
        assert panel._is_muted(ChannelName.PULSE1)


class TestMuteStateReading:
    @pytest.mark.parametrize(
        "muted, expected",
        [
            (frozenset(), set()),
            (frozenset({ChannelName.PULSE1}), {ChannelName.PULSE1}),
            (frozenset(ChannelName.items()), set(ChannelName.items())),
        ],
        ids=["full mix", "one silenced", "every channel silenced"],
    )
    def test_is_muted_follows_the_pushed_model(
        self,
        muted: FrozenSet[ChannelName],
        expected: FrozenSet[ChannelName],
    ) -> None:
        panel = _panel(muted)

        reported = {channel for channel in ChannelName.items() if panel._is_muted(channel)}

        assert reported == expected

    def test_no_channel_reads_as_muted_before_a_model_arrives(self) -> None:
        panel = _panel(frozenset())
        panel._current_channels = None

        assert not any(panel._is_muted(channel) for channel in ChannelName.items())


class TestChannelTintColour:
    @pytest.mark.parametrize(
        "channel, expected",
        [
            (ChannelName.PULSE1, (240, 146, 86, 128)),
            (ChannelName.PULSE2, (242, 209, 95, 128)),
            (ChannelName.TRIANGLE, (140, 193, 237, 128)),
            (ChannelName.NOISE, (187, 184, 194, 128)),
        ],
        ids=lambda value: value.value if isinstance(value, ChannelName) else "",
    )
    def test_audible_tint_is_the_identity_colour_at_the_configured_fraction(
        self,
        channel: ChannelName,
        expected: Tuple[int, int, int, int],
    ) -> None:
        panel = _panel(frozenset())

        assert panel._channel_column_tint(channel) == expected
