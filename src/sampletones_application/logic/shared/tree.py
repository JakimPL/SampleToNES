import threading
from typing import Callable, Optional

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.shared.file_playback import FilePlayback
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.structures.tree import FileSystemNode, NodeType, TreeNode
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class TreeLogic(CallbackMixin):
    def __init__(
        self,
        session_manager: SessionManager,
        file_playback: FilePlayback,
        *,
        scheduling: SchedulingBehavior,
    ) -> None:
        self._session_manager = session_manager
        self._file_playback = file_playback
        self._scheduling = scheduling

        self._lock_counter: int = 0
        self._is_locked: bool = False
        self._thread_lock = threading.RLock()

        self._pending_autoplay_node: Optional[FileSystemNode] = None
        self._pending_search_query: Optional[str] = None

        self.on_lock_state_changed: Optional[Callable[[bool], None]] = None
        self.on_favorite_changed: Optional[Callable[[FileSystemNode], None]] = None
        self.on_search_update_needed: Optional[VoidCallback] = None

    def lock(self) -> None:
        with self._thread_lock:
            self._lock_counter += 1
            self._is_locked = True

        self._notify_lock_state(False)

    def unlock(self) -> None:
        with self._thread_lock:
            self._lock_counter -= 1
            unlocked = self._lock_counter <= 0
            if unlocked:
                self._lock_counter = 0
                self._is_locked = False

        if unlocked:
            self._notify_lock_state(True)

    def _notify_lock_state(self, is_unlocked: bool) -> None:
        """Deliver the tree-enabled change on the main thread.

        A rebuild toggles the lock from a background worker, and the bound listener flips the
        tree's enabled state in DearPyGui. Routing it through the callback queue keeps that
        widget work on the thread that owns the context.
        """
        callback = self.on_lock_state_changed
        if callback is not None:
            CallbackQueue.add(
                callback,
                is_unlocked,
                priority=self._scheduling.priorities.gui_action,
            )

    @property
    def locked(self) -> bool:
        with self._thread_lock:
            return self._is_locked

    def request_autoplay(self, node: FileSystemNode) -> None:
        self._pending_autoplay_node = node
        CallbackQueue.add(
            self._execute_autoplay,
            priority=self._scheduling.priorities.schedule,
            delay=self._scheduling.delays.schedule,
        )

    def cancel_autoplay(self) -> None:
        self._pending_autoplay_node = None

    def play_node(self, node: FileSystemNode) -> None:
        """Play the file a browser node stands for, where it is one the player can sound."""
        if node.node_type == NodeType.FILE:
            self._file_playback.play(node.filepath)

    def is_playable_file(self, node: TreeNode) -> bool:
        """Whether the node is a file the player knows how to sound."""
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return False

        return FilePlayback.plays(node.filepath)

    def _execute_autoplay(self) -> None:
        if self._pending_autoplay_node is not None:
            self._autoplay_file(self._pending_autoplay_node)
            self._pending_autoplay_node = None

    def _autoplay_file(self, node: FileSystemNode) -> None:
        """Sound what a selection selects, where the session says a selection sounds at all."""
        if self._session_manager.autoplay and node.node_type == NodeType.FILE:
            self._file_playback.play_at(node.filepath, PlaybackPriority.PREVIEW)

    def is_node_favorite(self, node: TreeNode) -> bool:
        if not isinstance(node, FileSystemNode):
            return False

        return node.filepath in self._session_manager.favorites

    def has_favorite_ancestor(self, node: FileSystemNode) -> bool:
        """Whether a favorite directory holds this path, at any depth above it.

        The answer reads the path rather than the rows above it, so it holds wherever a view puts
        the node: a reconstruction listed under the sample it came from sits below groups the
        browser invented, and the directory that makes it a favorite child is still on its path.
        """
        favorites = self._session_manager.favorites
        return any(directory in favorites for directory in node.filepath.parents)

    def toggle_favorite(self, node: FileSystemNode) -> None:
        self._session_manager.toggle_favorite(node.filepath)
        self.call(self.on_favorite_changed, node)

    def schedule_search_update(self, query: str) -> None:
        self._pending_search_query = query
        CallbackQueue.add(
            self._execute_search_update,
            priority=self._scheduling.priorities.schedule,
            delay=self._scheduling.delays.schedule,
        )

    def _execute_search_update(self) -> None:
        if self._pending_search_query is not None:
            self._pending_search_query = None
            self.call(self.on_search_update_needed)

    @property
    def autoplay_enabled(self) -> bool:
        return self._session_manager.autoplay

    @property
    def auto_expand_favorite_reconstructions(self) -> bool:
        return self._session_manager.auto_expand_favorite_reconstructions

    @property
    def auto_expand_favorite_directories(self) -> bool:
        return self._session_manager.auto_expand_favorite_directories
