import threading
from typing import Callable, Optional

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core import paths
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures.tree import FileSystemNode, NodeType, TreeNode
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class TreeLogic(CallbackMixin):
    def __init__(
        self,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        *,
        scheduling: SchedulingBehavior,
    ) -> None:
        self._session_manager = session_manager
        self._audio_device_manager = audio_device_manager
        self._scheduling = scheduling

        self._lock_counter: int = 0
        self._is_locked: bool = False
        self._thread_lock = threading.RLock()

        self._pending_autoplay_node: Optional[FileSystemNode] = None
        self._pending_search_query: Optional[str] = None

        self.on_lock_state_changed: Optional[Callable[[bool], None]] = None
        self.on_favorite_changed: Optional[Callable[[FileSystemNode], None]] = None
        self.on_search_update_needed: Optional[VoidCallback] = None
        self.on_autoplay_error: Optional[Callable[[Exception], None]] = None

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
            CallbackQueue.add(callback, is_unlocked, priority=self._scheduling.priorities.gui_action)

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
        """Play a file on demand, preempting the auxiliary preview and the players.

        Unlike autoplay this ignores the session autoplay flag and uses ``NORMAL``
        priority: it is a deliberate user action, so it always plays and outranks the
        reconstruction/sequencer players.
        """
        self._play_file(node, PlaybackPriority.NORMAL)

    def is_playable_file(self, node: TreeNode) -> bool:
        """Whether the node is a file this logic knows how to play (reconstruction or audio)."""
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return False

        suffix = node.filepath.suffix.lower()
        return suffix == paths.EXT_FILE_RECONSTRUCTION or suffix in paths.EXT_FILES_AUDIO

    def _execute_autoplay(self) -> None:
        if self._pending_autoplay_node is not None:
            self._autoplay_file(self._pending_autoplay_node)
            self._pending_autoplay_node = None

    def _autoplay_file(self, node: FileSystemNode) -> None:
        if self._session_manager.autoplay:
            self._play_file(node, PlaybackPriority.PREVIEW)

    def _play_file(self, node: FileSystemNode, priority: PlaybackPriority) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        match node.filepath.suffix.lower():
            case paths.EXT_FILE_RECONSTRUCTION:
                try:
                    reconstruction = Reconstruction.load(node.filepath)
                    self._audio_device_manager.play(
                        reconstruction.approximation,
                        update=False,
                        priority=priority,
                    )
                except (OSError, SampleToNESError) as exception:
                    logger.error_with_traceback(exception, f"Failed to play reconstruction file: {node.filepath}")
                    self.call(self.on_autoplay_error, exception)
            case suffix if suffix in paths.EXT_FILES_AUDIO:
                self._audio_device_manager.play_file(
                    node.filepath,
                    update=False,
                    priority=priority,
                )

    def is_node_favorite(self, node: TreeNode) -> bool:
        if not isinstance(node, FileSystemNode):
            return False

        return node.filepath in self._session_manager.favorites

    def has_favorite_ancestor(self, node: FileSystemNode) -> bool:
        current_node = node.parent
        while current_node is not None:
            if not isinstance(current_node, FileSystemNode):
                break

            if self.is_node_favorite(current_node):
                return True

            current_node = current_node.parent

        return False

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
