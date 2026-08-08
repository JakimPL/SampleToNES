from dataclasses import dataclass, field
from typing import List, Tuple

import pytest

from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.view_model.sequencer.samples import SampleEntryViewModel
from tests.suite.shortcuts import shipped_source

ENTRIES: Tuple[SampleEntryViewModel, ...] = (
    SampleEntryViewModel(sample_id="kick-id", name="Kick", loop=False),
    SampleEntryViewModel(sample_id="bass-id", name="Bass", loop=True),
    SampleEntryViewModel(sample_id="lead-id", name="Lead", loop=False),
)

SELECTED_ID = "bass-id"
SELECTED_ROW = 1

Move = Tuple[str, int]


@dataclass
class SamplesPanelFixture:
    """A panel carrying the state the key path reads, with the calls each action makes recorded."""

    panel: GUISequencerSamplesPanel
    removed: List[str] = field(default_factory=list)
    moved: List[Move] = field(default_factory=list)
    renamed: List[str] = field(default_factory=list)
    cancelled: List[None] = field(default_factory=list)


@pytest.fixture
def samples(monkeypatch: pytest.MonkeyPatch) -> SamplesPanelFixture:
    panel = GUISequencerSamplesPanel.__new__(GUISequencerSamplesPanel)
    panel._shortcuts = shipped_source()
    panel._entries = ENTRIES
    panel._selected_sample_id = SELECTED_ID
    panel._selected_row = SELECTED_ROW
    panel._editing_sample_id = None

    fixture = SamplesPanelFixture(panel=panel)
    panel.on_remove_requested = fixture.removed.append
    panel.on_move_requested = lambda sample_id, target: fixture.moved.append((sample_id, target))
    monkeypatch.setattr(panel, "_start_rename", fixture.renamed.append)
    monkeypatch.setattr(panel, "_cancel_rename", lambda: fixture.cancelled.append(None))
    return fixture


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


class TestSelectedSampleActions:
    def test_the_remove_key_removes_the_selected_sample(self, samples: SamplesPanelFixture) -> None:
        assert samples.panel._on_key_pressed(_press("Del")) is True
        assert samples.removed == [SELECTED_ID]

    def test_the_rename_key_starts_the_rename(self, samples: SamplesPanelFixture) -> None:
        assert samples.panel._on_key_pressed(_press("F2")) is True
        assert samples.renamed == [SELECTED_ID]

    def test_a_press_the_panel_leaves_unnamed_reaches_the_application(self, samples: SamplesPanelFixture) -> None:
        assert samples.panel._on_key_pressed(_press("Ctrl+S")) is False
        assert samples.removed == []

    def test_a_press_without_a_selection_reaches_the_application(self, samples: SamplesPanelFixture) -> None:
        samples.panel._selected_sample_id = None

        assert samples.panel._on_key_pressed(_press("Del")) is False


class TestSampleMoves:
    def test_the_move_up_key_moves_the_sample_one_row_back(self, samples: SamplesPanelFixture) -> None:
        assert samples.panel._on_key_pressed(_press("Alt+Up")) is True
        assert samples.moved == [(SELECTED_ID, SELECTED_ROW - 1)]

    def test_the_move_to_bottom_key_moves_the_sample_last(self, samples: SamplesPanelFixture) -> None:
        assert samples.panel._on_key_pressed(_press("Alt+End")) is True
        assert samples.moved == [(SELECTED_ID, len(ENTRIES) - 1)]

    def test_a_move_with_nowhere_to_go_still_consumes_the_key(self, samples: SamplesPanelFixture) -> None:
        samples.panel._selected_row = 0

        assert samples.panel._on_key_pressed(_press("Alt+Up")) is True
        assert samples.moved == []


class TestRenameInProgress:
    def test_the_cancel_key_drops_the_name_being_edited(self, samples: SamplesPanelFixture) -> None:
        samples.panel._editing_sample_id = SELECTED_ID

        assert samples.panel._on_key_pressed(_press("Esc")) is True
        assert samples.cancelled == [None]

    def test_every_other_key_stays_with_the_field(self, samples: SamplesPanelFixture) -> None:
        """A rename keeps the keyboard, so typing a name reaches the input rather than the list."""
        samples.panel._editing_sample_id = SELECTED_ID

        assert samples.panel._on_key_pressed(_press("Del")) is False
        assert samples.removed == []
