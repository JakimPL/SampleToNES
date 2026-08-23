import contextlib
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, List, Optional, Tuple

import pytest

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.elements.sequencer import SequencerVoicesElements
from sampletones_application.ui.elements import context_menu as context_menu_module
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.panels.sequencer import voices as voices_module
from sampletones_application.ui.panels.sequencer.voices import VOICE_MOVES, GUISequencerVoicesPanel
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_application.view_model.sequencer.voices import VoiceEntryViewModel, VoiceKind
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.footprint import InstrumentFootprint
from sampletones_core.utils.display import display_voice_label
from sampletones_shared.types.callback import VoidCallback
from tests.suite.shortcuts import shipped_source

ENTRIES: Tuple[VoiceEntryViewModel, ...] = (
    VoiceEntryViewModel(voice_id="kick-id", name="Kick", kind=VoiceKind.SAMPLE, loop=False),
    VoiceEntryViewModel(voice_id="bass-id", name="Bass", kind=VoiceKind.SAMPLE, loop=True),
    VoiceEntryViewModel(voice_id="lead-id", name="Lead", kind=VoiceKind.SAMPLE, loop=False),
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

RIGHT_BUTTON = 1

EDIT_ITEM = 0
RENAME_ITEM = 1
DUPLICATE_ITEM = 2
REMOVE_ITEM = 3
MOVE_UP_ITEM = 4
MOVE_DOWN_ITEM = 5
MOVE_TOP_ITEM = 6
MOVE_BOTTOM_ITEM = 7
EXPORT_ITEM = 8

ONE_INSTRUMENT: Tuple[Optional[ChannelName], ...] = (ChannelName.PULSE1,)
TWO_INSTRUMENTS: Tuple[Optional[ChannelName], ...] = (ChannelName.PULSE1, ChannelName.NOISE)
NO_INSTRUMENTS: Tuple[Optional[ChannelName], ...] = ()


def _unreachable() -> None:
    """Stands where a greyed-out item would carry a callback, which a reader never fires."""


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
    pool: List[str] = field(default_factory=list)
    exported: List[Tuple[str, Optional[ChannelName]]] = field(default_factory=list)


class _MenuRecorder:
    def __init__(self) -> None:
        self.items: List[MenuItem] = []
        self.submenus: List[str] = []

    @contextlib.contextmanager
    def menu(self, **kwargs: Any) -> Iterator[None]:
        self.submenus.append(kwargs["label"])
        yield

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(
            MenuItem(
                label=kwargs["label"],
                shortcut=kwargs.get("shortcut", ""),
                enabled=kwargs.get("enabled", True),
                callback=kwargs.get("callback", _unreachable),
            )
        )
        return 0


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    recorded = _MenuRecorder()
    monkeypatch.setattr(voices_module.dpg, "add_menu_item", recorded.add_menu_item)
    monkeypatch.setattr(voices_module.dpg, "add_separator", lambda **_kwargs: 0)
    monkeypatch.setattr(voices_module.dpg, "menu", recorded.menu)
    return recorded


@dataclass
class VoicesPanelFixture:
    """A panel holding a selection, with the calls each menu item makes recorded."""

    panel: GUISequencerVoicesPanel
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
    instruments: Tuple[Optional[ChannelName], ...] = ONE_INSTRUMENT,
) -> VoicesPanelFixture:
    """A samples panel whose menu builder can run with no DearPyGui context behind it."""
    panel = GUISequencerVoicesPanel.__new__(GUISequencerVoicesPanel)
    panel._language_manager = _Labels()
    panel._shortcuts = shipped_source()
    panel._entries = ENTRIES
    panel._selected_voice_id = None if selected_row is None else SELECTED_ID
    panel._selected_row = selected_row
    panel._editing_voice_id = editing
    panel._list_menu_pending = False
    panel._tab_active = lambda: tab_active
    panel._router = _Router(field_focused=field_focused)
    panel._detail_color = DETAIL_COLOR
    panel._lbl_sample_size = SAMPLE_SIZE_LABEL
    panel._tpl_size_bytes = SIZE_TEMPLATE
    panel._tip_size_bytes = SIZE_TOOLTIP
    panel.sample_footprint = (lambda _voice_id: footprint) if footprint_wired else None
    panel.voice_instruments = lambda _voice_id: instruments

    requests = Requests()
    panel.on_sample_edit_requested = requests.edited.append
    panel.on_duplicate_requested = requests.duplicated.append
    panel.on_remove_requested = requests.removed.append
    panel.on_move_requested = lambda voice_id, target: requests.moved.append((voice_id, target))
    panel.on_new_instrument_requested = lambda: requests.pool.append(SequencerVoicesElements.NEW_INSTRUMENT.value)
    panel.on_add_sample_requested = lambda: requests.pool.append(SequencerVoicesElements.ADD_SAMPLE.value)
    panel.on_import_instrument_requested = lambda: requests.pool.append(SequencerVoicesElements.IMPORT_INSTRUMENT.value)
    panel.on_export_instrument_requested = lambda voice_id, channel: requests.exported.append((voice_id, channel))
    monkeypatch.setattr(panel, "_start_rename", requests.renamed.append)
    return VoicesPanelFixture(panel=panel, requests=requests)


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

    @contextlib.contextmanager
    def menu(self, **kwargs: Any) -> Iterator[None]:
        self.widgets.append(MenuWidget(kind="menu", text=kwargs["label"]))
        yield

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


def _deferred_calls(monkeypatch: pytest.MonkeyPatch) -> List[VoidCallback]:
    """The callbacks handed to the next frame, which is where the list's menu waits."""
    deferred: List[VoidCallback] = []
    monkeypatch.setattr(
        voices_module.FrameCallbackManager,
        "set_frame_callback",
        lambda callback: deferred.append(callback),
    )
    return deferred


@pytest.fixture
def build_recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuBuildRecorder:
    """Records a whole context-menu build, with the DearPyGui calls behind it stood down."""
    recorded = _MenuBuildRecorder()
    monkeypatch.setattr(voices_module.dpg, "add_text", recorded.add_text)
    monkeypatch.setattr(voices_module.dpg, "add_separator", recorded.add_separator)
    monkeypatch.setattr(voices_module.dpg, "add_menu_item", recorded.add_menu_item)
    monkeypatch.setattr(voices_module.dpg, "menu", recorded.menu)
    monkeypatch.setattr(voices_module, "context_menu", _null_menu)
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
            SequencerVoicesElements.CONTEXT_EDIT.value,
            SequencerVoicesElements.CONTEXT_RENAME.value,
            SequencerVoicesElements.CONTEXT_DUPLICATE.value,
            SequencerVoicesElements.CONTEXT_REMOVE.value,
            *(move.element.value for move in VOICE_MOVES),
            SequencerVoicesElements.CONTEXT_EXPORT_INSTRUMENT.value,
        ]

    def test_the_items_print_the_keys_the_panel_answers_to(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        """The panel has always answered these presses, and an item prints the one it fires."""
        shortcuts = shipped_source()
        _panel(monkeypatch).panel.build_edit_actions()

        assert recorder.items[RENAME_ITEM].shortcut == shortcuts.display(ShortcutId.VOICES_RENAME_VOICE)
        assert recorder.items[REMOVE_ITEM].shortcut == shortcuts.display(ShortcutId.VOICES_REMOVE_VOICE)
        assert [item.shortcut for item in recorder.items[MOVE_UP_ITEM : MOVE_BOTTOM_ITEM + 1]] == [
            shortcuts.display(move.shortcut) for move in VOICE_MOVES
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
        assert fixture.requests.exported == [(SELECTED_ID, ChannelName.PULSE1)]

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


class TestExportingTheVoicesInstruments:
    """The menu offers what an export would write for the voice, however many instruments that is."""

    def test_a_voice_holding_one_instrument_offers_a_plain_item(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        """There is nothing to choose between, so the item writes the one instrument straight away."""
        _panel(monkeypatch).panel.build_edit_actions()

        assert recorder.submenus == []
        assert recorder.items[EXPORT_ITEM].label == SequencerVoicesElements.CONTEXT_EXPORT_INSTRUMENT.value

    def test_a_voice_holding_several_offers_one_item_per_channel(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        _panel(monkeypatch, instruments=TWO_INSTRUMENTS).panel.build_edit_actions()

        assert recorder.submenus == [SequencerVoicesElements.CONTEXT_EXPORT_INSTRUMENT.value]
        assert [item.label for item in recorder.items[EXPORT_ITEM:]] == [
            ContextElements.PULSE_1.value,
            ContextElements.NOISE.value,
        ]

    def test_each_channel_writes_the_instrument_it_names(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        fixture = _panel(monkeypatch, instruments=TWO_INSTRUMENTS)
        fixture.panel.build_edit_actions()

        for item in recorder.items[EXPORT_ITEM:]:
            item.callback()

        assert fixture.requests.exported == [
            (SELECTED_ID, ChannelName.PULSE1),
            (SELECTED_ID, ChannelName.NOISE),
        ]

    def test_an_instrument_stated_for_no_channel_is_named_after_its_voice(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        """A hand-written voice reads the same envelopes on every channel, so it carries its own name."""
        _panel(monkeypatch, instruments=(None, ChannelName.NOISE)).panel.build_edit_actions()

        assert recorder.items[EXPORT_ITEM].label == "Bass"

    def test_a_voice_writing_nothing_offers_an_item_it_cannot_reach(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        """The export exists for every voice, and this one has nothing yet to write."""
        fixture = _panel(monkeypatch, instruments=NO_INSTRUMENTS)
        fixture.panel.build_edit_actions()

        assert not recorder.items[EXPORT_ITEM].enabled
        assert fixture.requests.exported == []


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

        def _measure(voice_id: str) -> SampleFootprintViewModel:
            measured.append(voice_id)
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
            display_voice_label(SELECTED_ROW, "Bass"),
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

        assert build_recorder.texts_before_the_first_item() == [display_voice_label(SELECTED_ROW, "Bass")]


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


class TestVoiceMenuActions:
    """The menu bar's Voice group carries the same actions the row menu prints."""

    def test_the_chosen_voice_states_its_actions_under_a_rule(
        self,
        monkeypatch: pytest.MonkeyPatch,
        build_recorder: _MenuBuildRecorder,
    ) -> None:
        """The group lists the pool above them, so the voice's own actions are led by a divider."""
        _panel(monkeypatch).panel.build_voice_actions()

        kinds = [widget.kind for widget in build_recorder.widgets]
        items = [widget.text for widget in build_recorder.widgets if widget.kind == "item"]

        assert kinds[0] == "separator"
        assert items[0] == SequencerVoicesElements.CONTEXT_EDIT.value

    def test_no_voice_chosen_states_nothing_at_all(
        self,
        monkeypatch: pytest.MonkeyPatch,
        build_recorder: _MenuBuildRecorder,
    ) -> None:
        """A group with no voice to act on shows the ways one comes in, and no divider below."""
        _panel(monkeypatch, selected_row=None).panel.build_voice_actions()

        assert build_recorder.widgets == []


class TestThePoolItems:
    """Every door onto the list offers the ways a voice comes in, so adding one is never hidden."""

    def test_the_list_menu_prints_the_ways_a_voice_comes_in(
        self,
        monkeypatch: pytest.MonkeyPatch,
        build_recorder: _MenuBuildRecorder,
    ) -> None:
        fixture = _panel(monkeypatch)
        fixture.panel._list_menu_pending = True

        fixture.panel._show_list_menu()

        assert [widget.text for widget in build_recorder.widgets] == [
            SequencerVoicesElements.NEW_INSTRUMENT.value,
            SequencerVoicesElements.ADD_SAMPLE.value,
            SequencerVoicesElements.IMPORT_INSTRUMENT.value,
        ]

    def test_a_row_menu_carries_the_pool_section_below_the_voice_actions(
        self,
        monkeypatch: pytest.MonkeyPatch,
        build_recorder: _MenuBuildRecorder,
    ) -> None:
        """A row is where a reader already is, so the list's own offers stay within reach there."""
        _panel(monkeypatch).panel._show_context_menu(SELECTED_ROW, SELECTED_ID)

        items = [widget.text for widget in build_recorder.widgets if widget.kind == "item"]

        assert items[-3:] == [
            SequencerVoicesElements.NEW_INSTRUMENT.value,
            SequencerVoicesElements.ADD_SAMPLE.value,
            SequencerVoicesElements.IMPORT_INSTRUMENT.value,
        ]
        assert SequencerVoicesElements.CONTEXT_EDIT.value in items

    def test_each_item_prints_the_key_it_answers_to(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        """Every way a voice comes in is rebindable, so each item names the press that fires it."""
        shortcuts = shipped_source()
        _panel(monkeypatch).panel.add_pool_items()

        assert [item.shortcut for item in recorder.items] == [
            shortcuts.display(ShortcutId.NEW_INSTRUMENT),
            shortcuts.display(ShortcutId.ADD_SAMPLE_FROM_FILE),
            shortcuts.display(ShortcutId.IMPORT_INSTRUMENT),
        ]

    def test_the_items_ask_for_a_written_voice_and_for_a_located_one(
        self,
        monkeypatch: pytest.MonkeyPatch,
        recorder: _MenuRecorder,
    ) -> None:
        fixture = _panel(monkeypatch)
        fixture.panel.add_pool_items()

        for item in recorder.items:
            item.callback()

        assert fixture.requests.pool == [
            SequencerVoicesElements.NEW_INSTRUMENT.value,
            SequencerVoicesElements.ADD_SAMPLE.value,
            SequencerVoicesElements.IMPORT_INSTRUMENT.value,
        ]


class TestWhichDoorAnswersAPress:
    """The list and the row are offered the same press, the list first, so one of them answers it."""

    def test_a_press_on_the_list_holds_its_menu_for_a_frame(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fixture = _panel(monkeypatch)
        deferred = _deferred_calls(monkeypatch)
        monkeypatch.setattr(fixture.panel, "_pointer_within_list", lambda: True)

        fixture.panel._on_list_right_clicked(0, RIGHT_BUTTON)

        assert fixture.panel._list_menu_pending
        assert deferred == [fixture.panel._show_list_menu]

    def test_a_row_claiming_the_press_leaves_the_list_menu_unbuilt(
        self,
        monkeypatch: pytest.MonkeyPatch,
        build_recorder: _MenuBuildRecorder,
    ) -> None:
        fixture = _panel(monkeypatch)
        _deferred_calls(monkeypatch)
        monkeypatch.setattr(fixture.panel, "_pointer_within_list", lambda: True)
        monkeypatch.setattr(fixture.panel, "_show_context_menu", lambda _position, _voice_id: None)
        monkeypatch.setattr(voices_module.dpg, "get_item_user_data", lambda _item: (SELECTED_ROW, SELECTED_ID))

        fixture.panel._on_list_right_clicked(0, RIGHT_BUTTON)
        fixture.panel._on_sample_clicked(0, (RIGHT_BUTTON, 0))
        fixture.panel._show_list_menu()

        assert build_recorder.widgets == []

    def test_a_press_beyond_the_list_asks_for_no_menu(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fixture = _panel(monkeypatch)
        deferred = _deferred_calls(monkeypatch)
        monkeypatch.setattr(fixture.panel, "_pointer_within_list", lambda: False)

        fixture.panel._on_list_right_clicked(0, RIGHT_BUTTON)

        assert not fixture.panel._list_menu_pending
        assert deferred == []
