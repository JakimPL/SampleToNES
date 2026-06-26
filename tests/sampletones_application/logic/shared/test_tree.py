from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.tree import TreeLogic
from sampletones_core.structures.tree import FileSystemNode, NodeType, TreeNode


def _tree(
    session_manager: Optional[MagicMock] = None,
    audio_device_manager: Optional[MagicMock] = None,
    scheduling: Optional[SchedulingBehavior] = None,
) -> TreeLogic:
    if session_manager is None:
        session_manager = MagicMock()
        session_manager.autoplay = True
        session_manager.favorites = set()
    if audio_device_manager is None:
        audio_device_manager = MagicMock()
    if scheduling is None:
        scheduling = SchedulingBehavior(
            delay_gui_action=0,
            delay_schedule=0,
            delay_cancel=0,
            priority_update_status=0,
            priority_gui_action=0,
            priority_schedule=0,
            priority_add_handler=0,
            priority_add_node=0,
        )
    return TreeLogic(session_manager, audio_device_manager, scheduling=scheduling)


def _file_node(filepath: Path) -> FileSystemNode:
    return FileSystemNode(filepath.name, NodeType.FILE, filepath=filepath)


def _dir_node(filepath: Path) -> FileSystemNode:
    return FileSystemNode(filepath.name, NodeType.DIRECTORY, filepath=filepath)


class TestTreeLogicLocking:
    def test_locked_is_false_initially(self) -> None:
        tree = _tree()
        assert tree.locked is False

    def test_lock_sets_locked_true(self) -> None:
        tree = _tree()
        tree.lock()
        assert tree.locked is True

    def test_unlock_after_lock_restores_false(self) -> None:
        tree = _tree()
        tree.lock()
        tree.unlock()
        assert tree.locked is False

    def test_nested_lock_unlock_stays_locked_until_balanced(self) -> None:
        tree = _tree()
        tree.lock()
        tree.lock()
        tree.unlock()
        assert tree.locked is True
        tree.unlock()
        assert tree.locked is False

    def test_lock_fires_lock_state_changed_callback(self) -> None:
        tree = _tree()
        states: list[bool] = []
        tree.on_lock_state_changed = lambda state: states.append(state)
        tree.lock()
        assert states == [False]

    def test_unlock_fires_lock_state_changed_callback(self) -> None:
        tree = _tree()
        states: list[bool] = []
        tree.on_lock_state_changed = lambda state: states.append(state)
        tree.lock()
        tree.unlock()
        assert True in states


class TestTreeLogicAutoplay:
    def test_cancel_autoplay_clears_pending_node(self, tmp_path: Path) -> None:
        tree = _tree()
        node = _file_node(tmp_path / "audio.wav")
        tree._pending_autoplay_node = node
        tree.cancel_autoplay()
        assert tree._pending_autoplay_node is None

    def test_autoplay_wav_file_calls_play_file(self, tmp_path: Path) -> None:
        audio_device_manager = MagicMock()
        session_manager = MagicMock()
        session_manager.autoplay = True
        session_manager.favorites = set()
        tree = _tree(
            session_manager=session_manager,
            audio_device_manager=audio_device_manager,
        )
        node = _file_node(tmp_path / "audio.wav")
        tree.request_autoplay(node)
        audio_device_manager.play_file.assert_called_once_with(
            node.filepath,
            update=False,
            priority=PlaybackPriority.PREVIEW,
        )

    def test_autoplay_with_directory_node_is_no_op(self, tmp_path: Path) -> None:
        audio_device_manager = MagicMock()
        session_manager = MagicMock()
        session_manager.autoplay = True
        tree = _tree(
            session_manager=session_manager,
            audio_device_manager=audio_device_manager,
        )
        node = _dir_node(tmp_path / "mydir")
        tree.request_autoplay(node)
        audio_device_manager.play_file.assert_not_called()
        audio_device_manager.play.assert_not_called()

    def test_autoplay_when_session_autoplay_disabled_is_no_op(
        self,
        tmp_path: Path,
    ) -> None:
        audio_device_manager = MagicMock()
        session_manager = MagicMock()
        session_manager.autoplay = False
        tree = _tree(
            session_manager=session_manager,
            audio_device_manager=audio_device_manager,
        )
        node = _file_node(tmp_path / "audio.wav")
        tree.request_autoplay(node)
        audio_device_manager.play_file.assert_not_called()

    def test_autoplay_enabled_property_reflects_session(self) -> None:
        session_manager = MagicMock()
        session_manager.autoplay = True
        session_manager.favorites = set()
        tree = _tree(session_manager=session_manager)
        assert tree.autoplay_enabled is True


class TestTreeLogicPlayNode:
    def test_play_node_uses_normal_priority_and_ignores_autoplay(self, tmp_path: Path) -> None:
        audio_device_manager = MagicMock()
        session_manager = MagicMock()
        session_manager.autoplay = False
        session_manager.favorites = set()
        tree = _tree(
            session_manager=session_manager,
            audio_device_manager=audio_device_manager,
        )
        node = _file_node(tmp_path / "audio.wav")

        tree.play_node(node)

        audio_device_manager.play_file.assert_called_once_with(
            node.filepath,
            update=False,
            priority=PlaybackPriority.NORMAL,
        )

    def test_play_node_with_directory_is_no_op(self, tmp_path: Path) -> None:
        audio_device_manager = MagicMock()
        tree = _tree(audio_device_manager=audio_device_manager)
        node = _dir_node(tmp_path / "mydir")

        tree.play_node(node)

        audio_device_manager.play_file.assert_not_called()
        audio_device_manager.play.assert_not_called()


class TestTreeLogicIsPlayableFile:
    def test_reconstruction_file_is_playable(self, tmp_path: Path) -> None:
        assert _tree().is_playable_file(_file_node(tmp_path / "song.stn")) is True

    def test_audio_file_is_playable(self, tmp_path: Path) -> None:
        assert _tree().is_playable_file(_file_node(tmp_path / "audio.wav")) is True

    def test_non_playable_file_is_rejected(self, tmp_path: Path) -> None:
        assert _tree().is_playable_file(_file_node(tmp_path / "notes.txt")) is False

    def test_directory_is_not_playable(self, tmp_path: Path) -> None:
        assert _tree().is_playable_file(_dir_node(tmp_path / "mydir")) is False


class TestTreeLogicFavorites:
    def test_is_node_favorite_returns_false_for_non_filesystem_node(self) -> None:
        tree = _tree()
        node = TreeNode("non-fs", NodeType.FILE)
        assert tree.is_node_favorite(node) is False

    def test_is_node_favorite_returns_false_when_not_in_favorites(
        self,
        tmp_path: Path,
    ) -> None:
        session_manager = MagicMock()
        session_manager.favorites = set()
        tree = _tree(session_manager=session_manager)
        node = _file_node(tmp_path / "audio.wav")
        assert tree.is_node_favorite(node) is False

    def test_is_node_favorite_returns_true_when_in_favorites(
        self,
        tmp_path: Path,
    ) -> None:
        filepath = tmp_path / "audio.wav"
        session_manager = MagicMock()
        session_manager.favorites = {filepath}
        tree = _tree(session_manager=session_manager)
        node = _file_node(filepath)
        assert tree.is_node_favorite(node) is True

    def test_has_favorite_ancestor_returns_false_when_no_ancestors(
        self,
        tmp_path: Path,
    ) -> None:
        session_manager = MagicMock()
        session_manager.favorites = set()
        tree = _tree(session_manager=session_manager)
        node = _file_node(tmp_path / "audio.wav")
        assert tree.has_favorite_ancestor(node) is False

    def test_has_favorite_ancestor_returns_true_when_parent_is_favorite(
        self,
        tmp_path: Path,
    ) -> None:
        parent_path = tmp_path / "parent"
        session_manager = MagicMock()
        session_manager.favorites = {parent_path}
        tree = _tree(session_manager=session_manager)
        parent = _dir_node(parent_path)
        child = _file_node(tmp_path / "parent" / "child.wav")
        child.parent = parent
        assert tree.has_favorite_ancestor(child) is True

    def test_toggle_favorite_delegates_to_session(
        self,
        tmp_path: Path,
    ) -> None:
        session_manager = MagicMock()
        session_manager.favorites = set()
        tree = _tree(session_manager=session_manager)
        node = _file_node(tmp_path / "audio.wav")
        tree.toggle_favorite(node)
        session_manager.toggle_favorite.assert_called_once_with(node.filepath)

    def test_toggle_favorite_fires_on_favorite_changed_callback(
        self,
        tmp_path: Path,
    ) -> None:
        tree = _tree()
        fired: list[FileSystemNode] = []
        tree.on_favorite_changed = lambda node: fired.append(node)
        node = _file_node(tmp_path / "audio.wav")
        tree.toggle_favorite(node)
        assert fired == [node]


class TestTreeLogicSearch:
    def test_schedule_search_update_fires_on_search_update_needed(self) -> None:
        tree = _tree()
        fired: list[str] = []
        tree.on_search_update_needed = lambda: fired.append("search")
        tree.schedule_search_update("query")
        assert fired == ["search"]

    def test_schedule_search_update_clears_pending_query_after_execution(self) -> None:
        tree = _tree()
        tree.on_search_update_needed = lambda: None
        tree.schedule_search_update("test")
        assert tree._pending_search_query is None
