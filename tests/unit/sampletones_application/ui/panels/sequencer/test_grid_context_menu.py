import contextlib
from typing import Any, Iterator, List, Tuple

import pytest

from sampletones_application.ui.panels.sequencer import grid as grid_module
from sampletones_application.ui.panels.sequencer.grid import (
    OCTAVE_SEMITONES,
    SEMITONE_STEP,
    VOLUME_COARSE_STEP,
    VOLUME_FINE_STEP,
    GUISequencerGridPanel,
)
from sampletones_application.view_model.sequencer.samples import (
    SampleEntryViewModel,
    SequencerSamplesViewModel,
)
from sampletones_core.constants.enums import GeneratorName

SENDER_WIDGET_ID = 6099
"""A stand-in for the menu-item widget id DearPyGui passes as the callback's first
positional argument. The original bug let this id overwrite the step payload."""


_CONTEXT_LABELS = (
    "_lbl_context_set_instrument",
    "_lbl_context_no_samples",
    "_lbl_context_transpose_up",
    "_lbl_context_transpose_down",
    "_lbl_context_transpose_octave_up",
    "_lbl_context_transpose_octave_down",
    "_lbl_context_volume_up",
    "_lbl_context_volume_down",
    "_lbl_context_volume_up_coarse",
    "_lbl_context_volume_down_coarse",
)


def _panel() -> GUISequencerGridPanel:
    """Builds a panel without its DearPyGui-dependent constructor.

    The menu-dispatch methods touch only their hook attributes, the context
    labels, and ``CallbackMixin.call``, so a fully wired GUI context is
    unnecessary here. Labels carry no behaviour, so any placeholder text serves.
    """
    panel = GUISequencerGridPanel.__new__(GUISequencerGridPanel)
    for label in _CONTEXT_LABELS:
        setattr(panel, label, "")
    return panel


class _MenuItemRecorder:
    """Captures the ``user_data``/``callback`` pairs the builders register."""

    def __init__(self) -> None:
        self.items: List[Tuple[Any, Any]] = []

    def add_menu_item(self, **kwargs: Any) -> int:
        if "callback" in kwargs and "user_data" in kwargs:
            self.items.append((kwargs["user_data"], kwargs["callback"]))
        return 0

    def dispatch_as_dpg(self) -> None:
        """Fires each recorded callback the way DearPyGui does: sender first."""
        for user_data, callback in self.items:
            callback(SENDER_WIDGET_ID, None, user_data)


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuItemRecorder:
    instance = _MenuItemRecorder()
    monkeypatch.setattr(grid_module.dpg, "add_menu_item", instance.add_menu_item)

    @contextlib.contextmanager
    def _menu(**kwargs: Any) -> Iterator[None]:
        yield

    monkeypatch.setattr(grid_module.dpg, "menu", _menu)
    return instance


class TestMenuDispatchPreservesPayload:
    def test_transpose_items_pass_the_configured_step(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        deltas: List[int] = []
        panel.on_adjust_transpose = lambda row, generator, delta: deltas.append(delta)

        panel._add_transpose_items(2, GeneratorName.PULSE1)
        recorder.dispatch_as_dpg()

        assert deltas == [SEMITONE_STEP, -SEMITONE_STEP, OCTAVE_SEMITONES, -OCTAVE_SEMITONES]

    def test_volume_items_pass_the_configured_step(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        deltas: List[int] = []
        panel.on_adjust_volume = lambda row, generator, delta: deltas.append(delta)

        panel._add_volume_items(2, GeneratorName.PULSE1)
        recorder.dispatch_as_dpg()

        assert deltas == [VOLUME_FINE_STEP, -VOLUME_FINE_STEP, VOLUME_COARSE_STEP, -VOLUME_COARSE_STEP]

    def test_adjust_carries_the_clicked_row_and_channel(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        calls: List[Tuple[int, GeneratorName, int]] = []
        panel.on_adjust_transpose = lambda row, generator, delta: calls.append((row, generator, delta))

        panel._add_transpose_items(7, GeneratorName.TRIANGLE)
        recorder.dispatch_as_dpg()

        assert calls[0] == (7, GeneratorName.TRIANGLE, SEMITONE_STEP)

    def test_instrument_items_pass_the_sample_id(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        panel._current_samples = SequencerSamplesViewModel(
            samples=(SampleEntryViewModel(sample_id="lead-id", name="lead", loop=False),),
        )
        chosen: List[str] = []
        panel.on_set_row = lambda row, generator, sample_id, transpose, volume: chosen.append(sample_id)

        panel._add_instrument_submenu(0, GeneratorName.PULSE2)
        recorder.dispatch_as_dpg()

        assert chosen == ["lead-id"]
