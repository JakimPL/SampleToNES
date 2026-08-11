from contextlib import contextmanager
from typing import Any, Callable, Dict, FrozenSet, Iterator, List

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.playback import FollowMode
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.general import (
    TAG_GLOBAL_MENU_GROUP_EDIT_ACTIONS,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS,
)
from sampletones_application.ui import menu as menu_module
from sampletones_application.ui.menu import MenuBar
from sampletones_application.utils.gui.shortcuts.ids import (
    CHANNEL_SHORTCUT_IDS,
    FOLLOW_MODE_SHORTCUT_IDS,
    SAMPLE_EXPORT_SHORTCUT_IDS,
    ShortcutId,
)
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_core.constants.enums import GeneratorName

CHANNEL_NAMES = ["Pulse 1", "Pulse 2", "Triangle", "Noise"]
UNMUTE_ALL = "Unmute all channels"
FOLLOW_MODE_NAMES = {
    FollowMode.ROWS: "Follow rows",
    FollowMode.PATTERNS: "Follow patterns",
    FollowMode.OFF: "Don't follow",
}


class _ShortcutManagerRecorder:
    """Records the items a menu asks for, in place of the manager that would create them."""

    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []

    def add_menu_item(self, shortcut_id: ShortcutId, **kwargs: Any) -> None:
        self.items.append({"shortcut_id": shortcut_id, **kwargs})

    @property
    def labels(self) -> List[str]:
        return [item["label"] for item in self.items]

    def item(self, label: str) -> Dict[str, Any]:
        return next(item for item in self.items if item["label"] == label)


class _DearPyGuiRecorder:
    """Stands in for the framework, recording the values and enablement a menu applies."""

    def __init__(self) -> None:
        self.values: Dict[str, bool] = {}
        self.enabled: Dict[str, bool] = {}
        self.menus: List[Dict[str, Any]] = []
        self.items: List[Dict[str, Any]] = []
        self.containers: List[str] = []
        self.emptied: List[str] = []

    @contextmanager
    def menu(self, **kwargs: Any) -> Iterator[int]:
        self.menus.append(kwargs)
        yield 0

    def submenu(self, tag: str) -> Dict[str, Any]:
        return next(entry for entry in self.menus if entry.get("tag") == tag)

    def add_separator(self, **kwargs: Any) -> int:
        return 0

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(kwargs)
        return 0

    @contextmanager
    def container(self, tag: str) -> Iterator[None]:
        self.containers.append(tag)
        yield

    def delete_children(self, tag: str) -> None:
        self.emptied.append(tag)

    def set_value(self, item: str, value: bool) -> None:
        self.values[item] = value

    def configure_item(self, item: str, **kwargs: Any) -> None:
        self.enabled[item] = kwargs["enabled"]


def _state(
    muted: FrozenSet[GeneratorName],
    *,
    reconstruction_loaded: bool = False,
    follow_mode: FollowMode = FollowMode.OFF,
) -> MenuBarViewModel:
    return MenuBarViewModel(
        project_open=True,
        reconstruction_loaded=reconstruction_loaded,
        reconstruction_saveable=False,
        reconstruction_in_project=False,
        reconstruction_file_backed=False,
        reconstruction_audio_recorded=False,
        operation_active=False,
        can_undo=False,
        can_redo=False,
        play_label="Play",
        play_or_pause_enabled=False,
        play_from_start_enabled=False,
        play_from_frame_enabled=False,
        pause_enabled=False,
        player_paused=False,
        stop_enabled=False,
        autoplay=False,
        follow_mode=follow_mode,
        loop_song=False,
        channels=SequencerChannelsViewModel(muted=muted),
        fullscreen=False,
        advanced_settings=False,
    )


@pytest.fixture
def framework(monkeypatch: pytest.MonkeyPatch) -> _DearPyGuiRecorder:
    instance = _DearPyGuiRecorder()
    monkeypatch.setattr(menu_module.dpg, "menu", instance.menu)
    monkeypatch.setattr(menu_module.dpg, "add_separator", instance.add_separator)
    monkeypatch.setattr(menu_module.dpg, "add_menu_item", instance.add_menu_item)
    monkeypatch.setattr(menu_module, "dpg_set_value", instance.set_value)
    monkeypatch.setattr(menu_module, "dpg_configure_item", instance.configure_item)
    monkeypatch.setattr(menu_module, "dpg_container", instance.container)
    monkeypatch.setattr(menu_module, "dpg_delete_children", instance.delete_children)
    return instance


@pytest.fixture
def shortcuts() -> _ShortcutManagerRecorder:
    return _ShortcutManagerRecorder()


@pytest.fixture
def switched() -> List[GeneratorName]:
    """The channels the bar asks the sequencer to switch, in the order it asks."""
    return []


@pytest.fixture
def menu_bar(
    shortcuts: _ShortcutManagerRecorder,
    switched: List[GeneratorName],
) -> MenuBar:
    """A bar with the collaborators its Channels submenu reads, from the real language file."""
    instance = MenuBar.__new__(MenuBar)
    instance._shortcut_manager = shortcuts
    instance._language_manager = LanguageManager(LANG_EN)
    instance._on_channel_muted = switched.append
    return instance


class TestInstrumentsExportMenu:
    """Each tracker that writes a file per slice gets its own item, so choosing the tracker
    is one click and the destination dialog then offers that tracker's type alone."""

    def test_every_offered_tracker_is_listed(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
        shortcuts: _ShortcutManagerRecorder,
    ) -> None:
        menu_bar._create_reconstruction_menu(_state(frozenset()))

        entries = [item for item in shortcuts.items if item["shortcut_id"] in SAMPLE_EXPORT_SHORTCUT_IDS.values()]

        assert [entry["label"] for entry in entries] == [
            "FamiTracker instruments...",
            "Bitphase presets...",
        ]

    def test_the_submenu_waits_for_a_loaded_reconstruction(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
        shortcuts: _ShortcutManagerRecorder,
    ) -> None:
        menu_bar._create_reconstruction_menu(_state(frozenset()))

        assert framework.submenu(TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS)["enabled"] is False

    def test_the_submenu_is_offered_once_a_reconstruction_is_loaded(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
        shortcuts: _ShortcutManagerRecorder,
    ) -> None:
        menu_bar._create_reconstruction_menu(_state(frozenset(), reconstruction_loaded=True))

        assert framework.submenu(TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS)["enabled"] is True


class TestFollowMenuItems:
    """The three reaches stand as one choice, so the check names the reach in place."""

    def test_every_reach_is_offered(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._create_follow_menu(_state(frozenset()))

        assert shortcuts.labels == list(FOLLOW_MODE_NAMES.values())

    def test_each_reach_carries_its_own_action(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._create_follow_menu(_state(frozenset()))

        actions = [item["shortcut_id"] for item in shortcuts.items]
        assert actions == list(FOLLOW_MODE_SHORTCUT_IDS.values())

    def test_each_reach_carries_its_own_tag(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._create_follow_menu(_state(frozenset()))

        tags = [item["tag"] for item in shortcuts.items]
        assert tags == [MenuBar._follow_menu_item_tag(mode) for mode in FOLLOW_MODE_SHORTCUT_IDS]

    @pytest.mark.parametrize("mode", list(FollowMode), ids=str)
    def test_the_reach_in_place_is_the_one_checked(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
        mode: FollowMode,
    ) -> None:
        menu_bar._create_follow_menu(_state(frozenset(), follow_mode=mode))

        checked = [item["label"] for item in shortcuts.items if item["default_value"]]
        assert checked == [FOLLOW_MODE_NAMES[mode]]


class TestFollowMenuUpdate:
    @pytest.mark.parametrize("mode", list(FollowMode), ids=str)
    def test_the_check_moves_to_the_reach_in_place(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
        mode: FollowMode,
    ) -> None:
        menu_bar._update_follow_mode(_state(frozenset(), follow_mode=mode))

        assert framework.values == {
            MenuBar._follow_menu_item_tag(candidate): candidate is mode for candidate in FollowMode
        }


class TestChannelsMenuItems:
    def test_every_channel_is_named_in_the_tracker_order(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._create_channels_menu(_state(frozenset()))

        assert shortcuts.labels == [*CHANNEL_NAMES, UNMUTE_ALL]

    def test_each_channel_carries_its_own_action(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._create_channels_menu(_state(frozenset()))

        actions = [item["shortcut_id"] for item in shortcuts.items[:-1]]
        assert actions == list(CHANNEL_SHORTCUT_IDS.values())

    def test_choosing_a_channel_switches_the_sequencer_mix(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
        switched: List[GeneratorName],
    ) -> None:
        """The check beside an item names the sequencer's mix, so the item switches that mix
        wherever the reader stands, while the key printed beside it reads the tab in front."""
        menu_bar._create_channels_menu(_state(frozenset()))

        for item in shortcuts.items[:-1]:
            item["callback"]()

        assert switched == list(CHANNEL_SHORTCUT_IDS)

    def test_each_channel_carries_its_own_tag(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._create_channels_menu(_state(frozenset()))

        tags = [item["tag"] for item in shortcuts.items[:-1]]
        assert tags == [MenuBar._channel_menu_item_tag(generator) for generator in CHANNEL_SHORTCUT_IDS]

    def test_a_channel_is_checked_while_it_sounds(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._create_channels_menu(_state(frozenset({GeneratorName.TRIANGLE})))

        assert shortcuts.item("Pulse 1")["default_value"]
        assert not shortcuts.item("Triangle")["default_value"]

    @pytest.mark.parametrize(
        ("muted", "offered"),
        [
            (frozenset(), False),
            (frozenset({GeneratorName.NOISE}), True),
        ],
        ids=["full_mix_withholds_the_restore", "a_silenced_channel_offers_the_restore"],
    )
    def test_the_restore_is_offered_while_a_channel_is_silenced(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
        framework: _DearPyGuiRecorder,
        muted: FrozenSet[GeneratorName],
        offered: bool,
    ) -> None:
        menu_bar._create_channels_menu(_state(muted))

        assert shortcuts.item(UNMUTE_ALL)["enabled"] is offered


class TestChannelsMenuUpdate:
    def test_the_checks_follow_the_mute_set(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._update_channels(_state(frozenset({GeneratorName.PULSE2})))

        assert framework.values == {
            MenuBar._channel_menu_item_tag(GeneratorName.PULSE1): True,
            MenuBar._channel_menu_item_tag(GeneratorName.PULSE2): False,
            MenuBar._channel_menu_item_tag(GeneratorName.TRIANGLE): True,
            MenuBar._channel_menu_item_tag(GeneratorName.NOISE): True,
        }

    def test_the_restore_follows_the_mute_set(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._update_channels(_state(frozenset({GeneratorName.PULSE2})))

        assert framework.enabled == {TAG_GLOBAL_MENU_ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS: True}

    def test_a_full_mix_withholds_the_restore(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._update_channels(_state(frozenset()))

        assert framework.enabled == {TAG_GLOBAL_MENU_ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS: False}


def _edit_bar(build_edit_actions: Callable[[], bool]) -> MenuBar:
    """A bar holding what the Edit menu's trailing section reads, and nothing else."""
    instance = MenuBar.__new__(MenuBar)
    instance._language_manager = LanguageManager(LANG_EN)
    instance._build_edit_actions = build_edit_actions
    instance._edit_actions_frame = None
    return instance


class TestEditActionsSection:
    """The Edit menu carries the actions of the grid holding the cursor, and names them itself
    while no grid holds one."""

    def test_the_clipboard_actions_are_named_greyed_out_with_no_grid_focused(
        self,
        framework: _DearPyGuiRecorder,
    ) -> None:
        _edit_bar(lambda: False)._refresh_edit_actions()

        assert [item["label"] for item in framework.items] == ["Copy", "Cut", "Paste", "Delete"]
        assert [item["enabled"] for item in framework.items] == [False] * 4

    def test_a_focused_grid_states_its_own_actions(
        self,
        framework: _DearPyGuiRecorder,
    ) -> None:
        requests: List[bool] = []

        def build() -> bool:
            requests.append(True)
            return True

        _edit_bar(build)._refresh_edit_actions()

        assert requests == [True]
        assert framework.items == []

    def test_the_section_is_emptied_before_the_actions_are_stated(
        self,
        framework: _DearPyGuiRecorder,
    ) -> None:
        _edit_bar(lambda: False)._refresh_edit_actions()

        assert framework.emptied == [TAG_GLOBAL_MENU_GROUP_EDIT_ACTIONS]
        assert framework.containers == [TAG_GLOBAL_MENU_GROUP_EDIT_ACTIONS]


class TestEditActionsRefresh:
    """DearPyGui reports the section drawn once a frame while the menu stands open, so a gap in
    those reports is what marks a fresh opening."""

    def test_the_actions_are_stated_once_while_the_menu_stays_open(
        self,
        framework: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        frames = iter([10, 11, 12, 13])
        monkeypatch.setattr(menu_module.dpg, "get_frame_count", lambda: next(frames))
        requests: List[int] = []
        menu_bar = _edit_bar(lambda: bool(requests.append(1)))

        for _ in range(4):
            menu_bar._on_edit_actions_drawn(0, 0)

        assert len(requests) == 1

    def test_the_actions_are_stated_afresh_each_time_the_menu_is_opened(
        self,
        framework: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        frames = iter([10, 11, 40, 41])
        monkeypatch.setattr(menu_module.dpg, "get_frame_count", lambda: next(frames))
        requests: List[int] = []
        menu_bar = _edit_bar(lambda: bool(requests.append(1)))

        for _ in range(4):
            menu_bar._on_edit_actions_drawn(0, 0)

        assert len(requests) == 2
