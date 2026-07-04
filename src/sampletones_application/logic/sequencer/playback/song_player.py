from typing import Callable, FrozenSet, Optional, Protocol

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.services.song_player.result import (
    SongPlaybackError,
    SongPlaybackStopped,
    SongPlayerResult,
    SongPositionUpdate,
)
from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.utils.callbacks import CallbackMixin


class SongPlayerServiceProtocol(Protocol):
    """The slice of the song-player service the playback logic drives.

    Typing the collaborator structurally keeps the logic layer bound to the
    service's result contract alone; the coordinator supplies the real service.
    """

    @property
    def alive(self) -> bool: ...

    @property
    def is_playing(self) -> bool: ...

    @property
    def is_paused(self) -> bool: ...

    def subscribe(self, handler: Callable[[SongPlayerResult], None]) -> None: ...

    def start(
        self,
        *,
        order_position: int,
        row_index: int,
        active_channels: FrozenSet[GeneratorName],
    ) -> None: ...

    def stop(self) -> None: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def seek(self, order_position: int) -> None: ...

    def relocate(self, order_position: int) -> None: ...


class SongPlayerLogic(CallbackMixin):
    """Bridges song-player service results to the coordinator.

    All playback controls are forwarded here from the UI panel. Position
    updates are forwarded to the coordinator via callbacks.
    """

    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        project_controller: ProjectController,
        session_manager: SessionManager,
        *,
        service: SongPlayerServiceProtocol,
    ) -> None:
        self._audio_device_manager = audio_device_manager
        self._project_controller = project_controller
        self._session_manager = session_manager
        self._service = service
        self._service.subscribe(self._on_service_result)
        self._audio_device_manager.on_acquire_output = self.stop
        self._audio_device_manager.external_output_priority = self._external_output_priority
        self._active_channels: FrozenSet[GeneratorName] = frozenset(GeneratorName.items())
        self._position = SongPosition()
        self._last_error: Optional[str] = None
        self._awaiting_seek_order: Optional[int] = None

        self.on_position_changed: Optional[Callable[[int, int], None]] = None
        self.on_view_changed: Optional[Callable[[SongPlayerViewModel], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    def play(self) -> None:
        self._last_error = None
        self._start_from(SongPosition())

    def play_from(self, order_position: int, row_index: int = 0) -> None:
        self._start_from(SongPosition(order_position=order_position, row_index=row_index))

    def _start_from(self, position: SongPosition) -> None:
        if not self._project_controller.is_open:
            return

        self._position = position
        self._awaiting_seek_order = None
        self._service.start(
            order_position=position.order_position,
            row_index=position.row_index,
            active_channels=self._active_channels,
        )
        self._emit_view()

    def pause_or_resume(self) -> None:
        if self._service.is_paused:
            self._service.resume()
        elif self._service.is_playing:
            self._service.pause()
        else:
            self.play()

        self._emit_view()

    def seek(self, order_position: int) -> None:
        """Moves the live playhead to another order, preserving sounding voices.

        Drives the follow-playback behaviour: selecting a different order while the song plays
        relocates the playhead in place. The service stays idle when nothing is playing.

        The worker emits each row's position only after its blocking write, so one in-flight update
        for the pre-seek order can still arrive. Recording the seek target lets ``_on_service_result``
        drop those stale updates until the playhead reports the new order, so the grid stays on the
        new order.
        """
        self._service.seek(order_position)
        if self._service.alive:
            self._awaiting_seek_order = order_position

    def relocate(self, order_position: int) -> None:
        """Follows a structural order edit, keeping playback on the frame it was sounding.

        Like :meth:`seek` but preserves the current row; stale in-flight updates for the
        pre-edit order are dropped via ``_awaiting_seek_order`` so the grid stays steady.
        """
        self._service.relocate(order_position)
        if self._service.alive:
            self._awaiting_seek_order = order_position

    def stop(self) -> None:
        self._service.stop()
        self._position = SongPosition()
        self._awaiting_seek_order = None
        self._emit_view()

    def is_playing(self) -> bool:
        return self._service.is_playing

    def is_paused(self) -> bool:
        return self._service.is_paused

    def is_loaded(self) -> bool:
        return self._project_controller.is_open

    @property
    def follow_playback(self) -> bool:
        return self._session_manager.follow_playback

    def set_follow_playback(self, value: bool) -> None:
        self._session_manager.set_follow_playback(value)
        self._emit_view()

    def _external_output_priority(self) -> Optional[int]:
        """The song holds the shared output device while its stream is alive (playing or paused)."""
        return PlaybackPriority.NORMAL if self._service.alive else None

    def set_active_channels(self, active_channels: FrozenSet[GeneratorName]) -> None:
        self._active_channels = active_channels

    def on_project_replaced(self) -> None:
        self.stop()

    def _on_service_result(self, result: SongPlayerResult) -> None:
        match result:
            case SongPositionUpdate(position=position):
                if self._awaiting_seek_order is not None and position.order_position != self._awaiting_seek_order:
                    return

                self._awaiting_seek_order = None
                self._position.order_position = position.order_position
                self._position.row_index = position.row_index
                self.call(self.on_position_changed, position.order_position, position.row_index)
                self._emit_view()
            case SongPlaybackStopped():
                self._position = SongPosition()
                self._awaiting_seek_order = None
                self._emit_idle_view()
            case SongPlaybackError(error=error):
                self._last_error = str(error) if str(error) else type(error).__name__
                self._position = SongPosition()
                self._awaiting_seek_order = None
                self.call(self.on_error, error)
                self._emit_view()

    def _emit_view(self) -> None:
        self.call(self.on_view_changed, self._build_view_model(self.is_playing(), self.is_paused()))

    def _emit_idle_view(self) -> None:
        """Pushes a definitively stopped view.

        ``SongPlaybackStopped`` is the authoritative end-of-playback signal, so the flags are
        forced off here. The worker thread may still be closing its audio stream and briefly report
        itself as playing; forcing the flags off keeps the stopped view authoritative and lets the
        playing highlight settle correctly.
        """
        self.call(self.on_view_changed, self._build_view_model(is_playing=False, is_paused=False))

    def _build_view_model(self, is_playing: bool, is_paused: bool) -> SongPlayerViewModel:
        return SongPlayerViewModel(
            is_loaded=self.is_loaded(),
            is_playing=is_playing,
            is_paused=is_paused,
            follow_playback=self.follow_playback,
            order_position=self._position.order_position,
            row_index=self._position.row_index,
            error=self._last_error,
        )
