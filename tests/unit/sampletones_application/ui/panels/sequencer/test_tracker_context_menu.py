import contextlib
from typing import Any, Iterator, List, Tuple

import pytest

from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.input.target import TrackerTarget
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.samples import (
    SampleEntryViewModel,
    SequencerSamplesViewModel,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.constants.music import OCTAVE_SEMITONES, SEMITONE_STEP
from tests.suite.shortcuts import shipped_source

SENDER_WIDGET_ID = 6099
"""A stand-in for the menu-item widget id DearPyGui passes as the callback's first
positional argument. The original bug let this id overwrite the step payload."""


_CONTEXT_LABELS = (
    "_lbl_context_set_instrument",
    "_lbl_context_no_samples",
)


def _panel() -> tracker_module.GUISequencerTrackerPanel:
    """Builds a panel without its DearPyGui-dependent constructor.

    The menu-dispatch methods touch only their hook attributes, the context
    labels, the keys each item prints, and ``CallbackMixin.call``, so a fully
    wired GUI context is unnecessary here. Labels carry no behaviour, so any
    placeholder text serves.
    """
    panel = tracker_module.GUISequencerTrackerPanel.__new__(tracker_module.GUISequencerTrackerPanel)
    for label in _CONTEXT_LABELS:
        setattr(panel, label, "")

    panel._lbl_adjust = {
        element: ""
        for element, _, _ in (
            *tracker_module.TRANSPOSE_ACTIONS,
            *tracker_module.VOLUME_ACTIONS,
        )
    }
    panel._shortcuts = shipped_source()
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
    monkeypatch.setattr(tracker_module.dpg, "add_menu_item", instance.add_menu_item)

    @contextlib.contextmanager
    def _menu(**kwargs: Any) -> Iterator[None]:
        yield

    monkeypatch.setattr(tracker_module.dpg, "menu", _menu)
    return instance


def _cell(row: int, channel: ChannelName) -> TrackerCursor:
    """The cell a menu was raised on, which the items carry as their payload."""
    return TrackerCursor(row, channel, SubColumn.INSTRUMENT)


def _target(row: int, channel: ChannelName) -> TrackerTarget:
    """The cell a menu was raised on, paired with the block of that cell alone."""
    cell = _cell(row, channel)
    return TrackerTarget(cell=cell, region=TrackerInputState().region_at(cell))


class TestMenuDispatchPreservesPayload:
    def test_transpose_items_pass_the_configured_step(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        deltas: List[int] = []
        panel.on_adjust_transpose = lambda region, delta: deltas.append(delta)

        panel._add_transpose_items(_target(2, ChannelName.PULSE1))
        recorder.dispatch_as_dpg()

        assert deltas == [
            SEMITONE_STEP,
            -SEMITONE_STEP,
            OCTAVE_SEMITONES,
            -OCTAVE_SEMITONES,
        ]

    def test_volume_items_pass_the_configured_step(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        deltas: List[int] = []
        panel.on_adjust_volume = lambda region, delta: deltas.append(delta)

        panel._add_volume_items(_target(2, ChannelName.PULSE1))
        recorder.dispatch_as_dpg()

        assert deltas == [
            tracker_module.VOLUME_FINE_STEP,
            -tracker_module.VOLUME_FINE_STEP,
            tracker_module.VOLUME_COARSE_STEP,
            -tracker_module.VOLUME_COARSE_STEP,
        ]

    def test_adjust_carries_the_block_the_menu_was_raised_on(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        calls: List[Tuple[TrackerRegion, int]] = []
        panel.on_adjust_transpose = lambda region, delta: calls.append((region, delta))
        target = _target(7, ChannelName.TRIANGLE)

        panel._add_transpose_items(target)
        recorder.dispatch_as_dpg()

        assert calls[0] == (target.region, SEMITONE_STEP)

    def test_instrument_items_pass_the_sample_id(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        panel._current_samples = SequencerSamplesViewModel(
            samples=(
                SampleEntryViewModel(
                    sample_id="lead-id",
                    name="lead",
                    loop=False,
                ),
            ),
        )
        chosen: List[str] = []
        panel.on_set_row = lambda row, channel, sample_id, transpose, volume: chosen.append(sample_id)

        panel._add_instrument_submenu(_cell(0, ChannelName.PULSE2))
        recorder.dispatch_as_dpg()

        assert chosen == ["lead-id"]
