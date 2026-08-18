from contextlib import contextmanager
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Tuple

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.playback import FollowMode
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.general import (
    TAG_GLOBAL_MENU_GROUP_EDIT,
    TAG_GLOBAL_MENU_GROUP_EDIT_MARKER,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS,
    TAG_GLOBAL_MENU_ITEM_VIEW_AUTO_EXPAND_FAVORITE_DIRECTORIES,
    TAG_GLOBAL_MENU_ITEM_VIEW_AUTO_EXPAND_FAVORITE_RECONSTRUCTIONS,
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

    def __init__(self, built: List[str]) -> None:
        self.items: List[Dict[str, Any]] = []
        self._built = built

    def add_menu_item(self, shortcut_id: ShortcutId, **kwargs: Any) -> None:
        self.items.append({"shortcut_id": shortcut_id, **kwargs})
        self._built.append(f"item:{kwargs['label']}")

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
        self.built: List[str] = []
        self.containers: List[str] = []
        self.deleted: List[int] = []

    @contextmanager
    def menu(self, **kwargs: Any) -> Iterator[int]:
        self.menus.append(kwargs)
        yield 0

    def submenu(self, tag: str) -> Dict[str, Any]:
        return next(entry for entry in self.menus if entry.get("tag") == tag)

    def add_separator(self, **kwargs: Any) -> int:
        self.built.append("separator")
        return 0

    def add_group(self, *, tag: str) -> int:
        self.built.append(f"group:{tag}")
        return 0

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(kwargs)
        self.built.append(f"item:{kwargs['label']}")
        return 0

    @contextmanager
    def item_handler_registry(self, **kwargs: Any) -> Iterator[int]:
        yield 0

    def add_item_visible_handler(self, **kwargs: Any) -> int:
        return 0

    def bind_item_handler_registry(self, item: str, registry: str) -> None:
        return None

    def append_items(self, tag: str, build: Callable[[], None]) -> Tuple[int, ...]:
        """Stands in for the helper that reports what one build left in the container."""
        self.containers.append(tag)
        standing = len(self.items)
        build()
        return tuple(range(standing, len(self.items)))

    def delete_item(self, item: int) -> None:
        self.deleted.append(item)

    def set_value(self, item: str, value: bool) -> None:
        self.values[item] = value

    def configure_item(self, item: str, **kwargs: Any) -> None:
        self.enabled[item] = kwargs["enabled"]


def _state(
    muted: FrozenSet[GeneratorName],
    *,
    reconstruction_loaded: bool = False,
    follow_mode: FollowMode = FollowMode.OFF,
    auto_expand_favorite_reconstructions: bool = False,
    auto_expand_favorite_directories: bool = False,
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
        auto_expand_favorite_reconstructions=auto_expand_favorite_reconstructions,
        auto_expand_favorite_directories=auto_expand_favorite_directories,
    )


@pytest.fixture
def framework(monkeypatch: pytest.MonkeyPatch) -> _DearPyGuiRecorder:
    instance = _DearPyGuiRecorder()
    monkeypatch.setattr(menu_module.dpg, "menu", instance.menu)
    monkeypatch.setattr(menu_module.dpg, "add_separator", instance.add_separator)
    monkeypatch.setattr(menu_module.dpg, "add_menu_item", instance.add_menu_item)
    monkeypatch.setattr(menu_module.dpg, "add_group", instance.add_group)
    monkeypatch.setattr(menu_module.dpg, "item_handler_registry", instance.item_handler_registry)
    monkeypatch.setattr(menu_module.dpg, "add_item_visible_handler", instance.add_item_visible_handler)
    monkeypatch.setattr(menu_module.dpg, "bind_item_handler_registry", instance.bind_item_handler_registry)
    monkeypatch.setattr(menu_module, "dpg_set_value", instance.set_value)
    monkeypatch.setattr(menu_module, "dpg_configure_item", instance.configure_item)
    monkeypatch.setattr(menu_module, "dpg_append_items", instance.append_items)
    monkeypatch.setattr(menu_module, "dpg_delete_item", instance.delete_item)
    return instance


@pytest.fixture
def shortcuts(framework: _DearPyGuiRecorder) -> _ShortcutManagerRecorder:
    return _ShortcutManagerRecorder(framework.built)


@pytest.fixture
def switched() -> List[GeneratorName]:
    """The channels the bar asks the sequencer to switch, in the order it asks."""
    return []


@pytest.fixture
def menu_bar(
    shortcuts: _ShortcutManagerRecorder,
    switched: List[GeneratorName],
) -> MenuBar:
    """A bar with the collaborators its submenus read, from the real language file."""
    instance = MenuBar.__new__(MenuBar)
    instance._shortcut_manager = shortcuts
    instance._language_manager = LanguageManager(LANG_EN)
    instance._on_channel_muted = switched.append
    instance._build_edit_actions = lambda: False
    instance._edit_actions_handler_tag = "handlers"
    instance._edit_actions_frame = None
    instance._edit_action_items = ()
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
    """A bar holding what the Edit menu's action section reads, and nothing else."""
    instance = MenuBar.__new__(MenuBar)
    instance._language_manager = LanguageManager(LANG_EN)
    instance._build_edit_actions = build_edit_actions
    instance._edit_actions_frame = None
    instance._edit_action_items = ()
    return instance


class TestAutoExpandFavoritesMenu:
    """Each kind of favorite is answered on its own, so the submenu offers one item per kind."""

    def test_both_kinds_are_offered(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
    ) -> None:
        menu_bar._create_auto_expand_favorites_menu()

        assert shortcuts.labels == ["Reconstructions", "Directories"]

    def test_each_kind_carries_its_own_action(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
    ) -> None:
        menu_bar._create_auto_expand_favorites_menu()

        assert [item["shortcut_id"] for item in shortcuts.items] == [
            ShortcutId.TOGGLE_AUTO_EXPAND_FAVORITE_RECONSTRUCTIONS,
            ShortcutId.TOGGLE_AUTO_EXPAND_FAVORITE_DIRECTORIES,
        ]

    def test_each_kind_is_offered_as_a_check(
        self,
        menu_bar: MenuBar,
        shortcuts: _ShortcutManagerRecorder,
    ) -> None:
        menu_bar._create_auto_expand_favorites_menu()

        assert all(item["check"] for item in shortcuts.items)

    def test_the_submenu_is_named_by_what_it_governs(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar._create_auto_expand_favorites_menu()

        assert [entry["label"] for entry in framework.menus] == ["Auto-expand favorites"]


class TestAutoExpandFavoritesUpdate:
    @pytest.mark.parametrize("reconstructions", [True, False])
    @pytest.mark.parametrize("directories", [True, False])
    def test_each_check_reads_the_preference_in_place(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
        reconstructions: bool,
        directories: bool,
    ) -> None:
        menu_bar._update_auto_expand_favorites(
            _state(
                frozenset(),
                auto_expand_favorite_reconstructions=reconstructions,
                auto_expand_favorite_directories=directories,
            )
        )

        assert framework.values == {
            TAG_GLOBAL_MENU_ITEM_VIEW_AUTO_EXPAND_FAVORITE_RECONSTRUCTIONS: reconstructions,
            TAG_GLOBAL_MENU_ITEM_VIEW_AUTO_EXPAND_FAVORITE_DIRECTORIES: directories,
        }


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

    def test_the_actions_are_stated_into_the_menu_itself(
        self,
        framework: _DearPyGuiRecorder,
    ) -> None:
        _edit_bar(lambda: False)._refresh_edit_actions()

        assert framework.containers == [TAG_GLOBAL_MENU_GROUP_EDIT]

    def test_a_build_takes_away_only_what_the_one_before_it_stated(
        self,
        framework: _DearPyGuiRecorder,
    ) -> None:
        menu_bar = _edit_bar(lambda: False)

        menu_bar._refresh_edit_actions()
        menu_bar._refresh_edit_actions()

        assert framework.deleted == [0, 1, 2, 3]


class TestEditMenuOrder:
    """The marker leads the Edit menu. A container standing below a menu item takes the width the
    items span as its own, and the popup grows to fit it on every frame it stays open."""

    def test_the_marker_stands_before_every_item(
        self,
        menu_bar: MenuBar,
        framework: _DearPyGuiRecorder,
        shortcuts: _ShortcutManagerRecorder,
    ) -> None:
        menu_bar._create_edit_menu(_state(frozenset()))

        assert framework.built == [
            f"group:{TAG_GLOBAL_MENU_GROUP_EDIT_MARKER}",
            "item:Undo",
            "item:Redo",
            "separator",
            "item:Copy",
            "item:Cut",
            "item:Paste",
            "item:Delete",
        ]


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
