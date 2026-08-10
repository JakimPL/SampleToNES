import contextlib
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN
from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.modifiers import Modifier
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

SENDER_WIDGET_ID: Sender = 8100
"""A stand-in for the handler-registry id DearPyGui passes as the callback's sender."""

STALE_WIDGET_ID: Sender = 8999
"""A header id a rebuild has already replaced, which the live map no longer names."""

LABEL_MUTE = "Mute"
LABEL_UNMUTE = "Unmute"
LABEL_SOLO = "Solo"
LABEL_UNSOLO = "Unsolo"
LABEL_MUTE_ALL = "Mute all channels"
LABEL_UNMUTE_ALL = "Unmute all channels"
ALL_CHANNEL_LABELS = [LABEL_MUTE_ALL, LABEL_UNMUTE_ALL]

COLUMN_LABELS: Dict[Optional[GeneratorName], str] = {
    None: "Sample",
    GeneratorName.PULSE1: "Pulse 1",
    GeneratorName.PULSE2: "Pulse 2",
    GeneratorName.TRIANGLE: "Triangle",
    GeneratorName.NOISE: "Noise",
}

HEADER_WIDGETS: Dict[Optional[GeneratorName], Sender] = {
    column: 200 + index for index, column in enumerate(COLUMN_LABELS)
}

FULL_MIX: FrozenSet[GeneratorName] = frozenset()
EVERY_CHANNEL: FrozenSet[GeneratorName] = frozenset(GeneratorName.items())


def _others(generator: GeneratorName) -> FrozenSet[GeneratorName]:
    """The mute set a solo of ``generator`` leaves behind."""
    return EVERY_CHANNEL - {generator}


class _MenuRecorder:
    """Captures the items a header menu builds, standing in for the DearPyGui popup."""

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


def _panel(muted: FrozenSet[GeneratorName]) -> GUISequencerTrackerPanel:
    """Builds a panel around the state the header menu reads, with no DearPyGui context.

    The menu touches the column labels, the pushed mute set, and the map from header widget to
    column, so those are wired directly and the rest of the panel is left out. The switch behind
    the menu is built the way the panel builds it, from the real language file, so the item labels
    under test are the ones a user reads.
    """
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._column_labels = dict(COLUMN_LABELS)
    panel._header_columns = {widget: column for column, widget in HEADER_WIDGETS.items()}
    panel._current_channels = SequencerChannelsViewModel(muted=muted)
    panel._create_channel_switch(LanguageManager(LANG_EN))
    return panel


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    instance = _MenuRecorder()
    monkeypatch.setattr(tracker_module.dpg, "add_menu_item", instance.add_menu_item)
    monkeypatch.setattr(tracker_module.dpg, "add_text", instance.add_text)
    monkeypatch.setattr(tracker_module.dpg, "add_separator", instance.add_separator)
    monkeypatch.setattr(tracker_module.FontRegistry, "bind_to_item", lambda item, font: None)

    @contextlib.contextmanager
    def _popup() -> Iterator[None]:
        yield

    monkeypatch.setattr(tracker_module, "context_menu", _popup)
    return instance


def _right_click(panel: GUISequencerTrackerPanel, column: Optional[GeneratorName]) -> None:
    panel._on_header_right_clicked(
        SENDER_WIDGET_ID,
        (dpg.mvMouseButton_Right, HEADER_WIDGETS[column]),
    )


class TestHeaderRightClickRouting:
    def test_a_right_click_opens_the_menu_for_the_clicked_column(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)

        _right_click(panel, GeneratorName.TRIANGLE)

        assert recorder.titles == [COLUMN_LABELS[GeneratorName.TRIANGLE]]

    def test_the_sample_header_opens_the_whole_mix_menu(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)

        _right_click(panel, None)

        assert recorder.titles == [COLUMN_LABELS[None]]
        assert recorder.labels == ALL_CHANNEL_LABELS

    @pytest.mark.parametrize(
        "mouse_button",
        [dpg.mvMouseButton_Left, dpg.mvMouseButton_Middle],
        ids=["left", "middle"],
    )
    def test_only_the_right_button_opens_the_menu(self, recorder: _MenuRecorder, mouse_button: int) -> None:
        panel = _panel(FULL_MIX)

        panel._on_header_right_clicked(
            SENDER_WIDGET_ID,
            (mouse_button, HEADER_WIDGETS[GeneratorName.NOISE]),
        )

        assert not recorder.titles

    def test_a_header_a_rebuild_replaced_opens_nothing(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)

        panel._on_header_right_clicked(SENDER_WIDGET_ID, (dpg.mvMouseButton_Right, STALE_WIDGET_ID))

        assert not recorder.titles

    def test_every_channel_header_reaches_its_own_menu(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)

        for generator in GeneratorName.items():
            _right_click(panel, generator)

        assert recorder.titles == [COLUMN_LABELS[generator] for generator in GeneratorName.items()]


class TestChannelItemLabels:
    @pytest.mark.parametrize(
        "muted, expected",
        [
            (FULL_MIX, LABEL_MUTE),
            (frozenset({GeneratorName.PULSE1}), LABEL_UNMUTE),
        ],
        ids=["audible", "silenced"],
    )
    def test_the_mute_item_names_the_change_it_makes(
        self,
        recorder: _MenuRecorder,
        muted: FrozenSet[GeneratorName],
        expected: str,
    ) -> None:
        panel = _panel(muted)

        _right_click(panel, GeneratorName.PULSE1)

        assert expected in recorder.labels

    @pytest.mark.parametrize(
        "muted, expected",
        [
            (FULL_MIX, LABEL_SOLO),
            (frozenset({GeneratorName.PULSE2}), LABEL_SOLO),
            (_others(GeneratorName.PULSE1), LABEL_UNSOLO),
        ],
        ids=["full mix", "another channel silenced", "already alone"],
    )
    def test_the_solo_item_names_the_change_it_makes(
        self,
        recorder: _MenuRecorder,
        muted: FrozenSet[GeneratorName],
        expected: str,
    ) -> None:
        panel = _panel(muted)

        _right_click(panel, GeneratorName.PULSE1)

        assert expected in recorder.labels

    def test_each_column_reads_its_own_state(self, recorder: _MenuRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.PULSE1}))

        _right_click(panel, GeneratorName.NOISE)

        assert LABEL_MUTE in recorder.labels

    def test_a_solo_elsewhere_leaves_this_channel_offering_a_solo(self, recorder: _MenuRecorder) -> None:
        """A silenced channel of a solo is offered its own solo, which moves the solo onto it."""
        panel = _panel(_others(GeneratorName.PULSE1))

        _right_click(panel, GeneratorName.PULSE2)

        assert LABEL_UNMUTE in recorder.labels
        assert LABEL_SOLO in recorder.labels

    def test_a_channel_menu_carries_both_blocks(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)

        _right_click(panel, GeneratorName.NOISE)

        assert recorder.labels == [LABEL_MUTE, LABEL_SOLO, *ALL_CHANNEL_LABELS]

    def test_the_sample_menu_addresses_no_single_channel(self, recorder: _MenuRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.NOISE}))

        _right_click(panel, None)

        assert LABEL_MUTE not in recorder.labels
        assert LABEL_UNMUTE not in recorder.labels
        assert LABEL_SOLO not in recorder.labels


class TestAllChannelItems:
    @pytest.mark.parametrize(
        "muted",
        [FULL_MIX, frozenset({GeneratorName.NOISE})],
        ids=["full mix", "one silenced"],
    )
    def test_muting_everything_is_offered_while_a_channel_sounds(
        self,
        recorder: _MenuRecorder,
        muted: FrozenSet[GeneratorName],
    ) -> None:
        panel = _panel(muted)

        _right_click(panel, None)

        assert recorder.is_enabled(LABEL_MUTE_ALL)

    def test_muting_everything_is_withheld_in_full_silence(self, recorder: _MenuRecorder) -> None:
        panel = _panel(EVERY_CHANNEL)

        _right_click(panel, None)

        assert not recorder.is_enabled(LABEL_MUTE_ALL)

    @pytest.mark.parametrize(
        "muted",
        [frozenset({GeneratorName.TRIANGLE}), EVERY_CHANNEL],
        ids=["one silenced", "every channel silenced"],
    )
    def test_restoring_everything_is_offered_while_a_channel_is_silent(
        self,
        recorder: _MenuRecorder,
        muted: FrozenSet[GeneratorName],
    ) -> None:
        panel = _panel(muted)

        _right_click(panel, None)

        assert recorder.is_enabled(LABEL_UNMUTE_ALL)

    def test_restoring_everything_is_withheld_in_the_full_mix(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)

        _right_click(panel, None)

        assert not recorder.is_enabled(LABEL_UNMUTE_ALL)

    def test_both_menus_end_with_the_whole_mix_items(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)

        _right_click(panel, GeneratorName.PULSE1)
        channel_menu = recorder.labels[-2:]
        _right_click(panel, None)

        assert channel_menu == ALL_CHANNEL_LABELS
        assert recorder.labels[-2:] == ALL_CHANNEL_LABELS


class TestHeaderMenuActions:
    def test_the_mute_item_switches_the_clicked_channel(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)
        toggled: List[GeneratorName] = []
        panel.on_channel_mute_toggled = toggled.append

        _right_click(panel, GeneratorName.TRIANGLE)
        recorder.click(LABEL_MUTE)

        assert toggled == [GeneratorName.TRIANGLE]

    def test_the_unmute_item_switches_the_clicked_channel(self, recorder: _MenuRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.TRIANGLE}))
        toggled: List[GeneratorName] = []
        panel.on_channel_mute_toggled = toggled.append

        _right_click(panel, GeneratorName.TRIANGLE)
        recorder.click(LABEL_UNMUTE)

        assert toggled == [GeneratorName.TRIANGLE]

    def test_the_solo_item_solos_the_clicked_channel(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)
        soloed: List[GeneratorName] = []
        panel.on_channel_soloed = soloed.append

        _right_click(panel, GeneratorName.NOISE)
        recorder.click(LABEL_SOLO)

        assert soloed == [GeneratorName.NOISE]

    def test_the_unsolo_item_takes_the_same_route_back(self, recorder: _MenuRecorder) -> None:
        """Leaving a solo restores the mix the solo interrupted, which the channels logic owns."""
        panel = _panel(_others(GeneratorName.NOISE))
        soloed: List[GeneratorName] = []
        panel.on_channel_soloed = soloed.append

        _right_click(panel, GeneratorName.NOISE)
        recorder.click(LABEL_UNSOLO)

        assert soloed == [GeneratorName.NOISE]

    def test_muting_everything_reaches_its_own_hook(self, recorder: _MenuRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.PULSE1}))
        muted: List[None] = []
        panel.on_channels_muted = lambda: muted.append(None)
        panel.on_channels_toggled = lambda: pytest.fail("the menu names the state it leaves")

        _right_click(panel, None)
        recorder.click(LABEL_MUTE_ALL)

        assert muted == [None]

    def test_restoring_everything_reaches_its_own_hook(self, recorder: _MenuRecorder) -> None:
        panel = _panel(frozenset({GeneratorName.PULSE1}))
        unmuted: List[None] = []
        panel.on_channels_unmuted = lambda: unmuted.append(None)
        panel.on_channels_toggled = lambda: pytest.fail("the menu names the state it leaves")

        _right_click(panel, None)
        recorder.click(LABEL_UNMUTE_ALL)

        assert unmuted == [None]

    def test_a_channel_menu_reaches_the_whole_mix_too(self, recorder: _MenuRecorder) -> None:
        panel = _panel(FULL_MIX)
        muted: List[None] = []
        panel.on_channels_muted = lambda: muted.append(None)

        _right_click(panel, GeneratorName.PULSE2)
        recorder.click(LABEL_MUTE_ALL)

        assert muted == [None]


class TestHeaderTooltips:
    @pytest.fixture
    def panel(self) -> GUISequencerTrackerPanel:
        instance = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
        instance._load_header_tooltips(LanguageManager(LANG_EN))
        return instance

    def test_the_channel_tooltip_names_the_solo_modifier(self, panel: GUISequencerTrackerPanel) -> None:
        assert Modifier.CTRL.value in panel._tooltip_header_channel

    def test_the_channel_tooltip_leaves_no_placeholder_behind(self, panel: GUISequencerTrackerPanel) -> None:
        assert "{" not in panel._tooltip_header_channel

    def test_both_headers_explain_their_click(self, panel: GUISequencerTrackerPanel) -> None:
        assert panel._tooltip_header_channel
        assert panel._tooltip_header_sample
        assert panel._tooltip_header_channel != panel._tooltip_header_sample
