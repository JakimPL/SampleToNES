from types import SimpleNamespace
from typing import Callable, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.ui.panels.sequencer.voices import panel as voices_module
from sampletones_application.ui.panels.sequencer.voices.panel import GUISequencerVoicesPanel
from sampletones_application.view_model.sequencer.voices import VoiceEntryViewModel, VoiceKind

ENTRIES: Tuple[VoiceEntryViewModel, ...] = (
    VoiceEntryViewModel(voice_id="kick-id", name="Kick", kind=VoiceKind.SAMPLE),
    VoiceEntryViewModel(voice_id="bass-id", name="Bass", kind=VoiceKind.SAMPLE),
)
MARKED_ID = "bass-id"
MARKED_ROW = 1
CLICKED_ID = "kick-id"
CLICKED_ROW = 0
ANY_ITEM = 7


@pytest.fixture(name="panel")
def panel_fixture(monkeypatch: pytest.MonkeyPatch) -> GUISequencerVoicesPanel:
    """A panel marking a voice and holding the keyboard, with its table calls stubbed out.

    The key scope reads the tab, the card and the router, which here all leave the panel free to
    answer, so what the cases read is the panel's own claim.
    """
    panel = GUISequencerVoicesPanel.__new__(GUISequencerVoicesPanel)
    panel._entries = ENTRIES
    panel._selected_voice_id = MARKED_ID
    panel._selected_row = MARKED_ROW
    panel._editing_voice_id = None
    panel._focused = True
    panel._mark_clear_pending = False
    panel._tab_active = lambda: True
    panel._router = SimpleNamespace(is_field_focused=False)
    panel.on_voice_selected = None
    monkeypatch.setattr(panel, "card_open", lambda: True)
    monkeypatch.setattr(panel, "_highlight_selected_row", lambda position: None)
    monkeypatch.setattr(voices_module.dpg, "unhighlight_table_row", lambda table, row: None)
    monkeypatch.setattr(voices_module.dpg, "set_value", lambda item, value: None)
    return panel


@pytest.fixture(name="deferred")
def deferred_fixture(monkeypatch: pytest.MonkeyPatch) -> List[Callable[[], None]]:
    """The callbacks the panel asks to run a frame later, held for a case to run."""
    deferred: List[Callable[[], None]] = []
    monkeypatch.setattr(voices_module.FrameCallbackManager, "set_frame_callback", deferred.append)
    return deferred


class TestTheMarkOutlivesTheKeyboard:
    """A marked voice holds the keys until a cell elsewhere takes them, and stays marked while they are away."""

    def test_a_marked_voice_holds_the_keys(self, panel: GUISequencerVoicesPanel) -> None:
        assert panel._keys_active() is True

    def test_blur_yields_the_keys_and_keeps_the_mark(self, panel: GUISequencerVoicesPanel) -> None:
        panel.blur()

        assert panel._keys_active() is False
        assert panel.selection is not None
        assert panel.selection.voice_id == MARKED_ID

    def test_a_row_click_takes_the_keys_back(self, panel: GUISequencerVoicesPanel) -> None:
        panel.blur()

        panel._on_voice_selected(ANY_ITEM, False, (CLICKED_ROW, CLICKED_ID))

        assert panel._keys_active() is True
        assert panel.selection is not None
        assert panel.selection.voice_id == CLICKED_ID

    def test_deselect_drops_the_mark_and_the_keys(self, panel: GUISequencerVoicesPanel) -> None:
        panel.deselect()

        assert panel.selection is None
        assert panel._keys_active() is False


class TestAPressBelowTheRows:
    """A left press on the empty foot of the list clears the mark a frame later, and a row landed on keeps it."""

    def test_the_press_clears_the_mark_a_frame_later(
        self,
        panel: GUISequencerVoicesPanel,
        deferred: List[Callable[[], None]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(panel, "_pointer_within_list", lambda: True)

        panel._on_list_left_clicked(ANY_ITEM, 0)

        assert panel.selection is not None
        (clear,) = deferred
        clear()
        assert panel.selection is None

    def test_a_row_answering_the_press_keeps_the_mark(
        self,
        panel: GUISequencerVoicesPanel,
        deferred: List[Callable[[], None]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(panel, "_pointer_within_list", lambda: True)

        panel._on_list_left_clicked(ANY_ITEM, 0)
        panel._on_voice_clicked(ANY_ITEM, (dpg.mvMouseButton_Left, ANY_ITEM))
        (clear,) = deferred
        clear()

        assert panel.selection is not None

    def test_a_press_outside_the_list_changes_nothing(
        self,
        panel: GUISequencerVoicesPanel,
        deferred: List[Callable[[], None]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(panel, "_pointer_within_list", lambda: False)

        panel._on_list_left_clicked(ANY_ITEM, 0)

        assert deferred == []
        assert panel.selection is not None
