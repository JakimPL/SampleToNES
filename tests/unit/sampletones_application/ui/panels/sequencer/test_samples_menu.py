import contextlib
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, List, Optional, Tuple

import pytest

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.elements.sequencer import SequencerInstrumentsElements
from sampletones_application.ui.elements import context_menu as context_menu_module
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.panels.sequencer import samples as samples_module
from sampletones_application.ui.panels.sequencer.samples import SAMPLE_MOVES, GUISequencerSamplesPanel
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_application.view_model.sequencer.samples import SampleEntryViewModel
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.footprint import InstrumentFootprint
from sampletones_core.utils.display import display_sample_label
from tests.suite.shortcuts import shipped_source

ENTRIES: Tuple[SampleEntryViewModel, ...] = (
    SampleEntryViewModel(sample_id="kick-id", name="Kick", loop=False),
    SampleEntryViewModel(sample_id="bass-id", name="Bass", loop=True),
    SampleEntryViewModel(sample_id="lead-id", name="Lead", loop=False),
)

SELECTED_ID = "bass-id"
SELECTED_ROW = 1

SAMPLE_SIZE_LABEL = "Sample size"
SIZE_TEMPLATE = "{bytes} B"
SIZE_TOOLTIP = "Bytes a FamiTracker export spends."
DETAIL_COLOR = LiteralColor((0, 0, 0, 255))

PULSE_1_FOOTPRINT = InstrumentFootprint(instrument_bytes=9, sequence_bytes=32)
NOISE_FOOTPRINT = InstrumentFootprint(instrument_bytes=7, sequence_bytes=12)
PULSE_1_BYTES = PULSE_1_FOOTPRINT.total_bytes
NOISE_BYTES = NOISE_FOOTPRINT.total_bytes
FOOTPRINT = SampleFootprintViewModel.from_footprints(
    {
        ChannelName.PULSE1: PULSE_1_FOOTPRINT,
        ChannelName.NOISE: NOISE_FOOTPRINT,
    }
)

EDIT_ITEM = 0
RENAME_ITEM = 1
DUPLICATE_ITEM = 2
REMOVE_ITEM = 3
MOVE_UP_ITEM = 4
MOVE_DOWN_ITEM = 5
MOVE_TOP_ITEM = 6
MOVE_BOTTOM_ITEM = 7


@dataclass
class MenuItem:
    """One item as it was registered, which is the whole of what a reader sees and clicks."""

    label: str
    shortcut: str
    enabled: bool
    callback: Callable[[], None]


@dataclass
class Requests:
    """What each sample hook was handed when its menu item fired."""

    edited: List[str] = field(default_factory=list)
    renamed: List[str] = field(default_factory=list)
    duplicated: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    moved: List[Tuple[str, Optional[int]]] = field(default_factory=list)


class _MenuRecorder:
    def __init__(self) -> None:
        self.items: List[MenuItem] = []

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(
            MenuItem(
                label=kwargs["label"],
                shortcut=kwargs.get("shortcut", ""),
                enabled=kwargs.get("enabled", True),
                callback=kwargs["callback"],
            )
        )
        return 0


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    recorded = _MenuRecorder()
    monkeypatch.setattr(samples_module.dpg, "add_menu_item", recorded.add_menu_item)
    monkeypatch.setattr(samples_module.dpg, "add_separator", lambda **_kwargs: 0)
    return recorded


@dataclass
class SamplesPanelFixture:
    """A panel holding a selection, with the calls each menu item makes recorded."""

    panel: GUISequencerSamplesPanel
    requests: Requests


def _panel(
    monkeypatch: pytest.MonkeyPatch,
    *,
    selected_row: Optional[int] = SELECTED_ROW,
    tab_active: bool = True,
    editing: Optional[str] = None,
    field_focused: bool = False,
    footprint: Optional[SampleFootprintViewModel] = FOOTPRINT,
    footprint_wired: bool = True,
) -> SamplesPanelFixture:
    """A samples panel whose menu builder can run with no DearPyGui context behind it."""
    panel = GUISequencerSamplesPanel.__new__(GUISequencerSamplesPanel)
    panel._language_manager = _Labels()
    panel._shortcuts = shipped_source()
    panel._entries = ENTRIES
    panel._selected_sample_id = None if selected_row is None else SELECTED_ID
    panel._selected_row = selected_row
    panel._editing_sample_id = editing
    panel._tab_active = lambda: tab_active
    panel._router = _Router(field_focused=field_focused)
    panel._detail_color = DETAIL_COLOR
    panel._lbl_sample_size = SAMPLE_SIZE_LABEL
    panel._tpl_size_bytes = SIZE_TEMPLATE
    panel._tip_size_bytes = SIZE_TOOLTIP
    panel.sample_footprint = (lambda _sample_id: footprint) if footprint_wired else None

    requests = Requests()
    panel.on_sample_edit_requested = requests.edited.append
    panel.on_duplicate_requested = requests.duplicated.append
    panel.on_remove_requested = requests.removed.append
    panel.on_move_requested = lambda sample_id, target: requests.moved.append((sample_id, target))
    monkeypatch.setattr(panel, "_start_rename", requests.renamed.append)
    return SamplesPanelFixture(panel=panel, requests=requests)


class _Labels:
    """A language manager printing each key's own element, so an item reads as the action it names."""

    def __getitem__(self, key: Tuple[Any, ...]) -> str:
        return str(key[-1].value)


@dataclass(frozen=True)
class MenuWidget:
    """One widget as the menu registered it, which is the whole of what a reader meets."""

    kind: str
    text: str


class _MenuBuildRecorder:
    """Every widget a whole menu build registers, in the order they are printed."""

    def __init__(self) -> None:
        self.widgets: List[MenuWidget] = []
        self.tooltips: List[str] = []

    def add_text(self, text: str, **_kwargs: Any) -> int:
        self.widgets.append(MenuWidget(kind="text", text=text))
        return 0

    def add_tooltip(self, _parent: int, message: str, **_kwargs: Any) -> int:
        self.tooltips.append(message)
        return 0

    def add_separator(self, **_kwargs: Any) -> int:
        self.widgets.append(MenuWidget(kind="separator", text=""))
        return 0

    def add_menu_item(self, **kwargs: Any) -> int:
        self.widgets.append(MenuWidget(kind="item", text=kwargs["label"]))
        return 0

    def texts_before_the_first_item(self) -> List[str]:
        widgets: List[str] = []
        for widget in self.widgets:
            if widget.kind == "item":
                break
            if widget.kind == "text":
                widgets.append(widget.text)

        return widgets


@contextlib.contextmanager
def _null_menu() -> Iterator[None]:
    yield


@pytest.fixture
def build_recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuBuildRecorder:
    """Records a whole context-menu build, with the DearPyGui calls behind it stood down."""
    recorded = _MenuBuildRecorder()
    monkeypatch.setattr(samples_module.dpg, "add_text", recorded.add_text)
    monkeypatch.setattr(samples_module.dpg, "add_separator", recorded.add_separator)
    monkeypatch.setattr(samples_module.dpg, "add_menu_item", recorded.add_menu_item)
    monkeypatch.setattr(samples_module, "context_menu", _null_menu)
    monkeypatch.setattr(context_menu_module, "dpg_set_palette_color", lambda _item, _color: None)
    monkeypatch.setattr(context_menu_module, "show_tooltip", recorded.add_tooltip)
    monkeypatch.setattr(FontRegistry, "bind_to_item", lambda _item, _font: None)
    return recorded


@dataclass(frozen=True)
class _Router:
    """The key router as the panel's own scope reads it."""

    field_focused: bool

    @property
    def is_field_focused(self) -> bool:
        return self.field_focused


class TestActionItems:
    def test_the_menu_reads_as_the_sample_actions(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        _panel(monkeypatch).panel.build_edit_actions()

        assert [item.label for item in recorder.items] == [
            SequencerInstrumentsElements.CONTEXT_EDIT.value,
            SequencerInstrumentsElements.CONTEXT_RENAME.value,
            SequencerInstrumentsElements.CONTEXT_DUPLICATE.value,
            SequencerInstrumentsElements.CONTEXT_REMOVE.value,
            *(move.element.value for move in SAMPLE_MOVES),
        ]

    def test_the_items_print_the_keys_the_panel_answers_to(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        """The panel has always answered these presses, and an item prints the one it fires."""
        shortcuts = shipped_source()
        _panel(monkeypatch).panel.build_edit_actions()

        assert recorder.items[RENAME_ITEM].shortcut == shortcuts.display(ShortcutId.SAMPLES_RENAME_SAMPLE)
        assert recorder.items[REMOVE_ITEM].shortcut == shortcuts.display(ShortcutId.SAMPLES_REMOVE_SAMPLE)
        assert [item.shortcut for item in recorder.items[MOVE_UP_ITEM:]] == [
            shortcuts.display(move.shortcut) for move in SAMPLE_MOVES
        ]

    def test_the_items_act_on_the_sample_they_were_raised_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        fixture = _panel(monkeypatch)
        fixture.panel.build_edit_actions()

        for item in recorder.items:
            item.callback()

        assert fixture.requests.edited == [SELECTED_ID]
        assert fixture.requests.renamed == [SELECTED_ID]
        assert fixture.requests.duplicated == [SELECTED_ID]
        assert fixture.requests.removed == [SELECTED_ID]
        assert fixture.requests.moved == [
            (SELECTED_ID, SELECTED_ROW - 1),
            (SELECTED_ID, SELECTED_ROW + 1),
            (SELECTED_ID, 0),
            (SELECTED_ID, len(ENTRIES) - 1),
        ]

    def test_a_move_with_nowhere_to_go_is_greyed_out(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        _panel(monkeypatch, selected_row=0).panel.build_edit_actions()

        assert not recorder.items[MOVE_UP_ITEM].enabled
        assert not recorder.items[MOVE_TOP_ITEM].enabled
        assert recorder.items[MOVE_DOWN_ITEM].enabled
        assert recorder.items[MOVE_BOTTOM_ITEM].enabled


class TestTheSizeRows:
    """A sample's menu names the bytes it occupies, so what a pool costs is read where it is edited."""

    def test_the_rows_read_as_the_total_then_each_playing_channel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        items = _panel(monkeypatch).panel._footprint_items(SELECTED_ID)

        assert items == [
            (SAMPLE_SIZE_LABEL, f"{PULSE_1_BYTES + NOISE_BYTES} B"),
            (ContextElements.PULSE_1.value, f"{PULSE_1_BYTES} B"),
            (ContextElements.NOISE.value, f"{NOISE_BYTES} B"),
        ]

    def test_a_channel_standing_by_is_named_nowhere(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A channel that does not play is written by no export, so it costs nothing to name."""
        labels = [label for label, _value in _panel(monkeypatch).panel._footprint_items(SELECTED_ID)]

        assert ContextElements.PULSE_2.value not in labels
        assert ContextElements.TRIANGLE.value not in labels

    def test_the_figures_name_the_sample_the_pointer_landed_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The figures are asked for as the menu opens, so they answer for the row right-clicked."""
        measured: List[str] = []

        def _measure(sample_id: str) -> SampleFootprintViewModel:
            measured.append(sample_id)
            return FOOTPRINT

        fixture = _panel(monkeypatch)
        fixture.panel.sample_footprint = _measure

        fixture.panel._footprint_items("lead-id")

        assert measured == ["lead-id"]

    def test_a_sample_the_pool_has_dropped_prints_no_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert _panel(monkeypatch, footprint=None).panel._footprint_items(SELECTED_ID) == []

    def test_an_unwired_hook_prints_no_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A panel tolerates its hooks being unset until the coordinator wires them."""
        assert _panel(monkeypatch, footprint_wired=False).panel._footprint_items(SELECTED_ID) == []


class TestMenuComposition:
    def test_the_sizes_sit_between_the_sample_name_and_the_actions(
        self,
        monkeypatch: pytest.MonkeyPatch,
        build_recorder: _MenuBuildRecorder,
    ) -> None:
        """Pins where the figures are printed: under the name they belong to, above what can be done."""
        _panel(monkeypatch).panel._show_context_menu(SELECTED_ROW, SELECTED_ID)

        assert build_recorder.texts_before_the_first_item() == [
            display_sample_label(SELECTED_ROW, "Bass"),
            f"{SAMPLE_SIZE_LABEL}: {PULSE_1_BYTES + NOISE_BYTES} B",
            f"{ContextElements.PULSE_1.value}: {PULSE_1_BYTES} B",
            f"{ContextElements.NOISE.value}: {NOISE_BYTES} B",
        ]

    def test_every_figure_names_the_export_it_measures(
        self,
        monkeypatch: pytest.MonkeyPatch,
        build_recorder: _MenuBuildRecorder,
    ) -> None:
        """A byte count means one export, so each line a reader hovers says which one it counts."""
        _panel(monkeypatch).panel._show_context_menu(SELECTED_ROW, SELECTED_ID)

        assert build_recorder.tooltips == [SIZE_TOOLTIP] * 3

    def test_a_menu_with_no_figures_reads_as_it_always_has(
        self,
        monkeypatch: pytest.MonkeyPatch,
        build_recorder: _MenuBuildRecorder,
    ) -> None:
        _panel(monkeypatch, footprint=None).panel._show_context_menu(SELECTED_ROW, SELECTED_ID)

        assert build_recorder.texts_before_the_first_item() == [display_sample_label(SELECTED_ROW, "Bass")]


class TestEditActions:
    def test_the_panel_answers_while_it_holds_a_selection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert _panel(monkeypatch).panel.owns_edit_actions()

    def test_a_panel_holding_no_selection_stands_down(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The grids and this panel hold one selection between them, so one of them answers."""
        assert not _panel(monkeypatch, selected_row=None).panel.owns_edit_actions()

    def test_a_panel_on_a_tab_behind_stands_down(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A selection outlives a move to another tab, and the Edit menu follows the tab in front."""
        assert not _panel(monkeypatch, tab_active=False).panel.owns_edit_actions()

    def test_a_field_holding_the_keyboard_stands_the_panel_down(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert not _panel(monkeypatch, field_focused=True).panel.owns_edit_actions()

    def test_a_panel_holding_no_selection_builds_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        _panel(monkeypatch, selected_row=None).panel.build_edit_actions()

        assert recorder.items == []
