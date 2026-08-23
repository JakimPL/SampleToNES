from dataclasses import dataclass, field
from typing import List, Tuple

import pytest

from sampletones_application.ui.panels.sequencer.voices import GUISequencerVoicesPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.view_model.sequencer.voices import VoiceEntryViewModel, VoiceKind
from tests.suite.shortcuts import shipped_source

ENTRIES: Tuple[VoiceEntryViewModel, ...] = (
    VoiceEntryViewModel(voice_id="kick-id", name="Kick", kind=VoiceKind.SAMPLE, loop=False),
    VoiceEntryViewModel(voice_id="bass-id", name="Bass", kind=VoiceKind.SAMPLE, loop=True),
    VoiceEntryViewModel(voice_id="lead-id", name="Lead", kind=VoiceKind.SAMPLE, loop=False),
)

SELECTED_ID = "bass-id"
SELECTED_ROW = 1

Move = Tuple[str, int]


@dataclass
class VoicesPanelFixture:
    """A panel carrying the state the key path reads, with the calls each action makes recorded."""

    panel: GUISequencerVoicesPanel
    removed: List[str] = field(default_factory=list)
    moved: List[Move] = field(default_factory=list)
    renamed: List[str] = field(default_factory=list)
    cancelled: List[None] = field(default_factory=list)


@pytest.fixture
def voices(monkeypatch: pytest.MonkeyPatch) -> VoicesPanelFixture:
    panel = GUISequencerVoicesPanel.__new__(GUISequencerVoicesPanel)
    panel._shortcuts = shipped_source()
    panel._entries = ENTRIES
    panel._selected_voice_id = SELECTED_ID
    panel._selected_row = SELECTED_ROW
    panel._editing_voice_id = None

    fixture = VoicesPanelFixture(panel=panel)
    panel.on_remove_requested = fixture.removed.append
    panel.on_move_requested = lambda voice_id, target: fixture.moved.append((voice_id, target))
    monkeypatch.setattr(panel, "_start_rename", fixture.renamed.append)
    monkeypatch.setattr(panel, "_cancel_rename", lambda: fixture.cancelled.append(None))
    return fixture


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


class TestSelectedSampleActions:
    def test_the_remove_key_removes_the_selected_sample(self, voices: VoicesPanelFixture) -> None:
        assert voices.panel._on_key_pressed(_press("Del")) is True
        assert voices.removed == [SELECTED_ID]

    def test_the_rename_key_starts_the_rename(self, voices: VoicesPanelFixture) -> None:
        assert voices.panel._on_key_pressed(_press("F2")) is True
        assert voices.renamed == [SELECTED_ID]

    def test_a_press_the_panel_leaves_unnamed_reaches_the_application(self, voices: VoicesPanelFixture) -> None:
        assert voices.panel._on_key_pressed(_press("Ctrl+S")) is False
        assert voices.removed == []

    def test_a_press_without_a_selection_reaches_the_application(self, voices: VoicesPanelFixture) -> None:
        voices.panel._selected_voice_id = None

        assert voices.panel._on_key_pressed(_press("Del")) is False


class TestSampleMoves:
    def test_the_move_up_key_moves_the_sample_one_row_back(self, voices: VoicesPanelFixture) -> None:
        assert voices.panel._on_key_pressed(_press("Alt+Up")) is True
        assert voices.moved == [(SELECTED_ID, SELECTED_ROW - 1)]

    def test_the_move_to_bottom_key_moves_the_sample_last(self, voices: VoicesPanelFixture) -> None:
        assert voices.panel._on_key_pressed(_press("Alt+End")) is True
        assert voices.moved == [(SELECTED_ID, len(ENTRIES) - 1)]

    def test_a_move_with_nowhere_to_go_still_consumes_the_key(self, voices: VoicesPanelFixture) -> None:
        voices.panel._selected_row = 0

        assert voices.panel._on_key_pressed(_press("Alt+Up")) is True
        assert voices.moved == []


class TestRenameInProgress:
    def test_the_cancel_key_drops_the_name_being_edited(self, voices: VoicesPanelFixture) -> None:
        voices.panel._editing_voice_id = SELECTED_ID

        assert voices.panel._on_key_pressed(_press("Esc")) is True
        assert voices.cancelled == [None]

    def test_every_other_key_stays_with_the_field(self, voices: VoicesPanelFixture) -> None:
        """A rename keeps the keyboard, so typing a name reaches the input rather than the list."""
        voices.panel._editing_voice_id = SELECTED_ID

        assert voices.panel._on_key_pressed(_press("Del")) is False
        assert voices.removed == []
