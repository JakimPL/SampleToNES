import contextlib
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN
from sampletones_application.ui.panels.sequencer.input.target import TrackerTarget
from sampletones_application.ui.panels.sequencer.input.tracker import (
    TrackerCursor,
    TrackerInputState,
)
from sampletones_application.ui.panels.sequencer.tracker import adjust
from sampletones_application.ui.panels.sequencer.tracker import menu as menu_module
from sampletones_application.ui.panels.sequencer.tracker.menu import TrackerMenu
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.voices import VoiceEntryViewModel, VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.constants.music import OCTAVE_SEMITONES, SEMITONE_STEP
from tests.suite.shortcuts import shipped_source

SENDER_WIDGET_ID = 6099
"""A stand-in for the menu-item widget id DearPyGui passes as the callback's first
positional argument. The original bug let this id overwrite the step payload."""


class _MenuHost:
    """The panel surface a menu reads, wired to just what these cases touch."""

    def __init__(self) -> None:
        self.on_clear_row = None
        self.on_clear_subcolumn = None
        self.on_set_row = None
        self.on_set_note_off = None
        self.on_play_from_row = None
        self.on_play_from_frame = None
        self.on_adjust_transpose = None
        self.on_adjust_volume = None
        self._voices: Tuple[VoiceEntryViewModel, ...] = ()

    @property
    def edit_surface(self) -> Any:
        raise NotImplementedError

    @property
    def channel_switch(self) -> Any:
        raise NotImplementedError

    @property
    def channels(self) -> Any:
        return None

    @property
    def voices(self) -> Tuple[VoiceEntryViewModel, ...]:
        return self._voices

    def hold_voices(self, *voices: VoiceEntryViewModel) -> None:
        self._voices = voices

    def column_label(self, channel: Optional[ChannelName]) -> str:
        return ""

    def select_shape(self, shortcut_id: Any, cell: TrackerCursor) -> bool:
        return True


def _menu() -> Tuple[TrackerMenu, _MenuHost]:
    """A menu over a bare host, which is all the item builders under test reach."""
    host = _MenuHost()
    return (
        TrackerMenu(
            host,
            language_manager=LanguageManager(LANG_EN),
            shortcut_source=shipped_source(),
        ),
        host,
    )


class _MenuItemRecorder:
    """Captures the ``user_data``/``callback`` pairs the builders register."""

    def __init__(self) -> None:
        self.items: List[Tuple[Any, Any]] = []
        self.entries: List[Dict[str, Any]] = []

    def add_menu_item(self, **kwargs: Any) -> int:
        self.entries.append(kwargs)
        if "callback" in kwargs and "user_data" in kwargs:
            self.items.append((kwargs["user_data"], kwargs["callback"]))
        return 0

    def reachable(self, label: str) -> bool:
        """Whether the one item carrying ``label`` was offered enabled."""
        entries = [entry for entry in self.entries if entry["label"] == label]
        assert len(entries) == 1, f"{label!r} appears {len(entries)} times"
        return bool(entries[0]["enabled"])

    def dispatch_as_dpg(self) -> None:
        """Fires each recorded callback the way DearPyGui does: sender first."""
        for user_data, callback in self.items:
            callback(SENDER_WIDGET_ID, None, user_data)


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuItemRecorder:
    instance = _MenuItemRecorder()
    monkeypatch.setattr(menu_module.dpg, "add_menu_item", instance.add_menu_item)

    @contextlib.contextmanager
    def _menu(**kwargs: Any) -> Iterator[None]:
        yield

    monkeypatch.setattr(menu_module.dpg, "menu", _menu)
    return instance


def _cell(row: int, channel: Optional[ChannelName]) -> TrackerCursor:
    """The cell a menu was raised on, which the items carry as their payload."""
    return TrackerCursor(row, channel, SubColumn.VOICE)


def _target(row: int, channel: ChannelName) -> TrackerTarget:
    """The cell a menu was raised on, paired with the block of that cell alone."""
    cell = _cell(row, channel)
    return TrackerTarget(cell=cell, region=TrackerInputState().region_at(cell))


class TestMenuDispatchPreservesPayload:
    def test_transpose_items_pass_the_configured_step(self, recorder: _MenuItemRecorder) -> None:
        menu, panel = _menu()
        deltas: List[int] = []
        panel.on_adjust_transpose = lambda region, delta: deltas.append(delta)

        menu._add_transpose_items(_target(2, ChannelName.PULSE1))
        recorder.dispatch_as_dpg()

        assert deltas == [
            SEMITONE_STEP,
            -SEMITONE_STEP,
            OCTAVE_SEMITONES,
            -OCTAVE_SEMITONES,
        ]

    def test_volume_items_pass_the_configured_step(self, recorder: _MenuItemRecorder) -> None:
        menu, panel = _menu()
        deltas: List[int] = []
        panel.on_adjust_volume = lambda region, delta: deltas.append(delta)

        menu._add_volume_items(_target(2, ChannelName.PULSE1))
        recorder.dispatch_as_dpg()

        assert deltas == [
            adjust.VOLUME_FINE_STEP,
            -adjust.VOLUME_FINE_STEP,
            adjust.VOLUME_COARSE_STEP,
            -adjust.VOLUME_COARSE_STEP,
        ]

    def test_adjust_carries_the_block_the_menu_was_raised_on(self, recorder: _MenuItemRecorder) -> None:
        menu, panel = _menu()
        calls: List[Tuple[TrackerRegion, int]] = []
        panel.on_adjust_transpose = lambda region, delta: calls.append((region, delta))
        target = _target(7, ChannelName.TRIANGLE)

        menu._add_transpose_items(target)
        recorder.dispatch_as_dpg()

        assert calls[0] == (target.region, SEMITONE_STEP)

    def test_instrument_items_pass_the_voice_id(self, recorder: _MenuItemRecorder) -> None:
        menu, panel = _menu()
        panel.hold_voices(
            VoiceEntryViewModel(
                voice_id="lead-id",
                name="lead",
                kind=VoiceKind.SAMPLE,
            ),
        )
        chosen: List[str] = []
        panel.on_set_row = lambda row, channel, voice_id, transpose, volume: chosen.append(voice_id)

        menu._add_voice_submenu(_cell(0, ChannelName.PULSE2))
        recorder.dispatch_as_dpg()

        assert chosen == ["lead-id"]


class TestWhichVoicesAColumnOffers:
    """The whole pool is listed wherever the menu is raised; the column decides what is reachable."""

    SAMPLE_LABEL = "00 lead"
    INSTRUMENT_LABEL = "01 pad"

    @staticmethod
    def _menu_with_both_kinds() -> Tuple[TrackerMenu, "_MenuHost"]:
        menu, host = _menu()
        host.hold_voices(
            VoiceEntryViewModel(
                voice_id="lead-id",
                name="lead",
                kind=VoiceKind.SAMPLE,
            ),
            VoiceEntryViewModel(
                voice_id="pad-id",
                name="pad",
                kind=VoiceKind.INSTRUMENT,
            ),
        )
        return menu, host

    def test_a_channel_column_reaches_both_kinds(self, recorder: _MenuItemRecorder) -> None:
        menu, panel = self._menu_with_both_kinds()

        menu._add_voice_submenu(_cell(0, ChannelName.PULSE2))

        assert recorder.reachable(self.SAMPLE_LABEL) is True
        assert recorder.reachable(self.INSTRUMENT_LABEL) is True

    def test_the_sample_column_reaches_a_sample_alone(self, recorder: _MenuItemRecorder) -> None:
        menu, panel = self._menu_with_both_kinds()

        menu._add_voice_submenu(_cell(0, None))

        assert recorder.reachable(self.SAMPLE_LABEL) is True
        assert recorder.reachable(self.INSTRUMENT_LABEL) is False

    def test_the_sample_column_still_names_the_instrument_it_stands_by_for(
        self,
        recorder: _MenuItemRecorder,
    ) -> None:
        """An unreachable item says the voice exists while leaving it where it belongs."""
        menu, panel = self._menu_with_both_kinds()

        menu._add_voice_submenu(_cell(0, None))

        assert [entry["label"] for entry in recorder.entries] == [
            self.SAMPLE_LABEL,
            self.INSTRUMENT_LABEL,
        ]

    def test_an_empty_pool_offers_one_unreachable_item(self, recorder: _MenuItemRecorder) -> None:
        menu, _ = _menu()

        menu._add_voice_submenu(_cell(0, None))

        assert [entry["enabled"] for entry in recorder.entries] == [False]
