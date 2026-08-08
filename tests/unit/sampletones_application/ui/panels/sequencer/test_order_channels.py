import contextlib
from types import SimpleNamespace
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Tuple

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.tabs.sequencer.colors.channel import ChannelColors
from sampletones_application.paths import LANG_EN
from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer import channels as channels_module
from sampletones_application.ui.panels.sequencer import order as order_module
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.utils.gui.keyboard.modifiers import (
    CTRL,
    NO_MODIFIERS,
    ModifierSet,
)
from sampletones_application.utils.palette.colors.written import LiteralColor
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.types.application import ColorRGBA, Sender
from sampletones_shared.types.callback import VoidCallback

LABEL_WIDGET_ID: Sender = 9100
"""A stand-in for the row-label id DearPyGui passes as the callback's sender."""

STALE_WIDGET_ID: Sender = 9999
"""A row label a rebuild has already replaced, which the live map no longer names."""

POSITION_COUNT = 3
TINT_FRACTION = 0.5
MUTED_TEXT_FRACTION = 0.25

MUTED_BACKGROUND: ColorRGBA = (10, 8, 18, 96)
CHANNEL_COLORS = ChannelColors(
    pulse1=LiteralColor((240, 146, 86, 255)),
    pulse2=LiteralColor((242, 209, 95, 255)),
    triangle=LiteralColor((140, 193, 237, 255)),
    noise=LiteralColor((187, 184, 194, 255)),
)

LABEL_THEME = 1
MUTED_LABEL_THEME = 2
ENTRY_THEME = 3
MUTED_ENTRY_THEME = 4

LABEL_MUTE = "Mute"
LABEL_UNMUTE = "Unmute"
LABEL_SOLO = "Solo"
LABEL_UNSOLO = "Unsolo"
LABEL_MUTE_ALL = "Mute all channels"
LABEL_UNMUTE_ALL = "Unmute all channels"

ROW_LABELS: Dict[Optional[GeneratorName], str] = {
    None: "Master",
    GeneratorName.PULSE1: "Pulse 1",
    GeneratorName.PULSE2: "Pulse 2",
    GeneratorName.TRIANGLE: "Triangle",
    GeneratorName.NOISE: "Noise",
}

CHANNEL_TABLE_ROWS: Dict[GeneratorName, int] = {
    GeneratorName.PULSE1: 2,
    GeneratorName.PULSE2: 3,
    GeneratorName.TRIANGLE: 4,
    GeneratorName.NOISE: 5,
}
"""Each channel's table row: the master row, the divider beneath it, then the four channels."""

LABEL_WIDGETS: Dict[Optional[GeneratorName], Sender] = {row: 300 + index for index, row in enumerate(ROW_LABELS)}


def _entry_widget(generator: GeneratorName, position: int) -> int:
    return 2000 + 100 * GeneratorName.items().index(generator) + position


class _DearPyGuiRecorder:
    """Captures the DearPyGui calls the channel cues make, standing in for a live table."""

    def __init__(self) -> None:
        self.row_tints: Dict[int, ColorRGBA] = {}
        self.bound_themes: Dict[Sender, int] = {}
        self.released: List[Sender] = []

    def does_item_exist(self, item: Sender) -> bool:
        return True

    def highlight_table_row(self, table: str, row: int, color: ColorRGBA) -> None:
        self.row_tints[row] = color

    def bind_item_theme(self, item: Sender, theme: int) -> None:
        self.bound_themes[item] = theme

    def set_value(self, item: Sender, value: bool) -> None:
        self.released.append(item)


class _MenuRecorder:
    """Captures the items a row-label menu builds, standing in for the DearPyGui popup."""

    def __init__(self) -> None:
        self.titles: List[str] = []
        self.items: List[Tuple[str, bool]] = []
        self.callbacks: Dict[str, VoidCallback] = {}

    def add_menu_item(self, **kwargs: Any) -> int:
        label = kwargs["label"]
        self.items.append((label, kwargs.get("enabled", True)))
        self.callbacks[label] = kwargs["callback"]
        return 0

    def add_text(self, message: str, **kwargs: Any) -> int:
        self.titles.append(message)
        return 0

    def add_separator(self, **kwargs: Any) -> int:
        return 0

    @property
    def labels(self) -> List[str]:
        return [label for label, _ in self.items]

    def is_enabled(self, label: str) -> bool:
        return dict(self.items)[label]

    def click(self, label: str) -> None:
        """Fires a recorded item the way DearPyGui fires a zero-argument callback."""
        self.callbacks[label]()


def _panel(muted: FrozenSet[GeneratorName]) -> GUISequencerOrderPanel:
    """Builds a panel around the state the channel cues read, with no DearPyGui context.

    The cues touch the layout colours, the theme ids, the row labels, and the entry registry, so
    those are wired directly and the rest of the panel is left out. The switch behind the label is
    built the way the panel builds it, from the real language file, so the item labels under test
    are the ones a user reads.
    """
    panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
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
    panel._position_count = POSITION_COUNT
    panel._row_labels = dict(ROW_LABELS)
    panel._label_rows = {widget: row for row, widget in LABEL_WIDGETS.items()}
    panel._label_theme = LABEL_THEME
    panel._muted_label_theme = MUTED_LABEL_THEME
    panel._entry_theme = ENTRY_THEME
    panel._muted_entry_theme = MUTED_ENTRY_THEME
    panel._order = EditableCells()
    for generator in GeneratorName.items():
        for position in range(POSITION_COUNT):
            panel._order.register((generator, position), _entry_widget(generator, position))

    panel._create_channel_switch(LanguageManager(LANG_EN))
    return panel


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _DearPyGuiRecorder:
    instance = _DearPyGuiRecorder()
    monkeypatch.setattr(order_module.dpg, "does_item_exist", instance.does_item_exist)
    monkeypatch.setattr(order_module.dpg, "highlight_table_row", instance.highlight_table_row)
    monkeypatch.setattr(order_module.dpg, "bind_item_theme", instance.bind_item_theme)
    monkeypatch.setattr(order_module.dpg, "set_value", instance.set_value)
    return instance


@pytest.fixture
def menu(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    instance = _MenuRecorder()
    monkeypatch.setattr(order_module.dpg, "add_menu_item", instance.add_menu_item)
    monkeypatch.setattr(order_module.dpg, "add_text", instance.add_text)
    monkeypatch.setattr(order_module.dpg, "add_separator", instance.add_separator)
    monkeypatch.setattr(order_module.FontRegistry, "bind_to_item", lambda item, font: None)

    @contextlib.contextmanager
    def _popup() -> Iterator[None]:
        yield

    monkeypatch.setattr(order_module, "context_menu", _popup)
    return instance


def _hold(monkeypatch: pytest.MonkeyPatch, modifiers: ModifierSet) -> None:
    monkeypatch.setattr(channels_module, "capture_modifiers", lambda: modifiers)


def _right_click(panel: GUISequencerOrderPanel, row: Optional[GeneratorName]) -> None:
    panel._on_label_right_clicked(
        LABEL_WIDGET_ID,
        (order_module.dpg.mvMouseButton_Right, LABEL_WIDGETS[row]),
    )


class TestRowLabelClickDispatch:
    def test_plain_click_toggles_the_clicked_channel(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, NO_MODIFIERS)
        toggled: List[GeneratorName] = []
        panel.on_channel_mute_toggled = toggled.append

        panel._on_label_clicked(LABEL_WIDGET_ID, True, GeneratorName.TRIANGLE)

        assert toggled == [GeneratorName.TRIANGLE]

    def test_ctrl_click_solos_the_clicked_channel(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, CTRL)
        soloed: List[GeneratorName] = []
        panel.on_channel_soloed = soloed.append
        panel.on_channel_mute_toggled = lambda _: pytest.fail("Ctrl+click must not toggle")

        panel._on_label_clicked(LABEL_WIDGET_ID, True, GeneratorName.NOISE)

        assert soloed == [GeneratorName.NOISE]

    def test_master_label_switches_every_channel(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, NO_MODIFIERS)
        switches: List[None] = []
        panel.on_channels_toggled = lambda: switches.append(None)
        panel.on_channel_mute_toggled = lambda _: pytest.fail("the master label addresses no single channel")

        panel._on_label_clicked(LABEL_WIDGET_ID, True, None)

        assert switches == [None]

    @pytest.mark.parametrize(
        "row",
        list(ROW_LABELS),
        ids=lambda row: "master" if row is None else row.value,
    )
    def test_every_label_click_releases_the_selectable(
        self,
        recorder: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
        row: Optional[GeneratorName],
    ) -> None:
        panel = _panel(frozenset())
        _hold(monkeypatch, NO_MODIFIERS)
        panel.on_channels_toggled = lambda: None
        panel.on_channel_mute_toggled = lambda _: None

        panel._on_label_clicked(LABEL_WIDGET_ID, True, row)

        assert recorder.released == [LABEL_WIDGET_ID]


class TestRowWash:
    def test_audible_channel_keeps_its_identity_tint(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset())

        panel._apply_channel_cues()

        assert recorder.row_tints[CHANNEL_TABLE_ROWS[GeneratorName.PULSE1]] == (
            240,
            146,
            86,
            128,
        )

    def test_muted_channel_takes_the_neutral_wash(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.PULSE1}))

        panel._apply_channel_cues()

        assert recorder.row_tints[CHANNEL_TABLE_ROWS[GeneratorName.PULSE1]] == MUTED_BACKGROUND

    def test_the_other_channels_keep_their_tint_while_one_is_muted(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.TRIANGLE}))

        panel._apply_channel_cues()

        washed = {
            generator for generator, row in CHANNEL_TABLE_ROWS.items() if recorder.row_tints[row] == MUTED_BACKGROUND
        }
        assert washed == {GeneratorName.TRIANGLE}

    def test_the_master_row_carries_no_channel_wash(self, recorder: _DearPyGuiRecorder) -> None:
        """The master row stands for every channel, so it takes its own shade instead of a tint."""
        panel = _panel(frozenset(GeneratorName.items()))

        panel._apply_channel_cues()

        assert set(recorder.row_tints) == set(CHANNEL_TABLE_ROWS.values())

    def test_the_wash_matches_the_shade_the_tracker_column_takes(self, recorder: _DearPyGuiRecorder) -> None:
        """Both tables read the same colour, so a silenced channel looks the same in each."""
        panel = _panel(frozenset({GeneratorName.NOISE}))

        assert panel._channel_row_tint(GeneratorName.NOISE) == MUTED_BACKGROUND


class TestRowLabelShade:
    def test_muted_channel_label_takes_the_muted_shade(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.PULSE2}))

        panel._apply_channel_cues()

        assert recorder.bound_themes[LABEL_WIDGETS[GeneratorName.PULSE2]] == MUTED_LABEL_THEME

    def test_audible_channel_label_keeps_the_plain_shade(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.PULSE2}))

        panel._apply_channel_cues()

        assert recorder.bound_themes[LABEL_WIDGETS[GeneratorName.NOISE]] == LABEL_THEME

    def test_master_label_keeps_the_plain_shade_with_every_channel_muted(
        self,
        recorder: _DearPyGuiRecorder,
    ) -> None:
        panel = _panel(frozenset(GeneratorName.items()))

        panel._apply_channel_cues()

        assert recorder.bound_themes[LABEL_WIDGETS[None]] == LABEL_THEME


class TestEntryTextShade:
    def test_muted_channel_entries_take_the_dimmed_theme(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.TRIANGLE}))

        panel._apply_channel_cues()

        bound = {
            recorder.bound_themes[_entry_widget(GeneratorName.TRIANGLE, position)] for position in range(POSITION_COUNT)
        }
        assert bound == {MUTED_ENTRY_THEME}

    def test_audible_channel_entries_keep_the_full_theme(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.TRIANGLE}))

        panel._apply_channel_cues()

        bound = {
            recorder.bound_themes[_entry_widget(GeneratorName.PULSE1, position)] for position in range(POSITION_COUNT)
        }
        assert bound == {ENTRY_THEME}

    def test_unmuting_restores_the_full_theme(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.NOISE}))
        panel._apply_channel_cues()

        panel.update_channels(SequencerChannelsViewModel(muted=frozenset()))

        bound = {
            recorder.bound_themes[_entry_widget(GeneratorName.NOISE, position)] for position in range(POSITION_COUNT)
        }
        assert bound == {ENTRY_THEME}


class TestPushedModel:
    def test_the_pushed_model_is_kept_for_the_next_rebuild(self, recorder: _DearPyGuiRecorder) -> None:
        panel = _panel(frozenset())

        panel.update_channels(SequencerChannelsViewModel(muted=frozenset({GeneratorName.PULSE1})))

        assert panel._is_muted(GeneratorName.PULSE1)

    def test_a_panel_awaiting_its_first_model_reports_every_channel_audible(
        self,
        recorder: _DearPyGuiRecorder,
    ) -> None:
        panel = _panel(frozenset())
        panel._current_channels = None

        assert not any(panel._is_muted(generator) for generator in GeneratorName.items())


class TestRowLabelRightClickRouting:
    def test_a_right_click_opens_the_menu_for_the_clicked_row(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())

        _right_click(panel, GeneratorName.TRIANGLE)

        assert menu.titles == [ROW_LABELS[GeneratorName.TRIANGLE]]

    def test_the_master_label_opens_the_whole_mix_menu(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())

        _right_click(panel, None)

        assert menu.titles == [ROW_LABELS[None]]
        assert menu.labels == [LABEL_MUTE_ALL, LABEL_UNMUTE_ALL]

    def test_a_left_click_opens_no_menu(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())

        panel._on_label_right_clicked(
            LABEL_WIDGET_ID,
            (order_module.dpg.mvMouseButton_Left, LABEL_WIDGETS[GeneratorName.NOISE]),
        )

        assert menu.titles == []

    def test_a_replaced_label_opens_no_menu(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())

        panel._on_label_right_clicked(
            LABEL_WIDGET_ID,
            (order_module.dpg.mvMouseButton_Right, STALE_WIDGET_ID),
        )

        assert menu.titles == []

    def test_every_row_label_reaches_its_own_menu(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())

        for row in ROW_LABELS:
            _right_click(panel, row)

        assert menu.titles == list(ROW_LABELS.values())


class TestRowLabelMenuItems:
    def test_a_channel_menu_carries_its_own_gestures_and_the_whole_mix(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())

        _right_click(panel, GeneratorName.PULSE1)

        assert menu.labels == [LABEL_MUTE, LABEL_SOLO, LABEL_MUTE_ALL, LABEL_UNMUTE_ALL]

    def test_the_items_name_the_change_they_make(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset(GeneratorName.items()) - {GeneratorName.PULSE1})

        _right_click(panel, GeneratorName.PULSE1)

        assert menu.labels == [
            LABEL_MUTE,
            LABEL_UNSOLO,
            LABEL_MUTE_ALL,
            LABEL_UNMUTE_ALL,
        ]

    def test_muting_everything_is_withheld_in_full_silence(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset(GeneratorName.items()))

        _right_click(panel, GeneratorName.NOISE)

        assert not menu.is_enabled(LABEL_MUTE_ALL)
        assert menu.is_enabled(LABEL_UNMUTE_ALL)

    def test_restoring_everything_is_withheld_in_the_full_mix(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())

        _right_click(panel, GeneratorName.NOISE)

        assert menu.is_enabled(LABEL_MUTE_ALL)
        assert not menu.is_enabled(LABEL_UNMUTE_ALL)

    def test_the_mute_item_switches_the_clicked_channel(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())
        toggled: List[GeneratorName] = []
        panel.on_channel_mute_toggled = toggled.append
        _right_click(panel, GeneratorName.PULSE2)

        menu.click(LABEL_MUTE)

        assert toggled == [GeneratorName.PULSE2]

    def test_the_solo_item_solos_the_clicked_channel(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset())
        soloed: List[GeneratorName] = []
        panel.on_channel_soloed = soloed.append
        _right_click(panel, GeneratorName.TRIANGLE)

        menu.click(LABEL_SOLO)

        assert soloed == [GeneratorName.TRIANGLE]

    def test_the_whole_mix_items_reach_their_own_hooks(self, menu: _MenuRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.NOISE}))
        calls: List[str] = []
        panel.on_channels_muted = lambda: calls.append("muted")
        panel.on_channels_unmuted = lambda: calls.append("unmuted")
        _right_click(panel, None)

        menu.click(LABEL_MUTE_ALL)
        menu.click(LABEL_UNMUTE_ALL)

        assert calls == ["muted", "unmuted"]


class TestRowLabelTooltips:
    def test_the_channel_tooltip_names_the_solo_modifier(self) -> None:
        panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)

        panel._load_label_tooltips(LanguageManager(LANG_EN))

        assert "Ctrl+click" in panel._tooltip_label_channel

    def test_the_channel_tooltip_names_both_click_gestures(self) -> None:
        panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)

        panel._load_label_tooltips(LanguageManager(LANG_EN))

        assert "mute" in panel._tooltip_label_channel
        assert "solo" in panel._tooltip_label_channel

    def test_the_master_tooltip_speaks_for_every_channel(self) -> None:
        panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)

        panel._load_label_tooltips(LanguageManager(LANG_EN))

        assert "every channel" in panel._tooltip_label_master
