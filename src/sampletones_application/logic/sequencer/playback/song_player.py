from typing import Callable, FrozenSet, Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.services.song_player.player import SongPlayerService
from sampletones_application.services.song_player.result import (
    SongPlaybackError,
    SongPlaybackStopped,
    SongPlayerResult,
    SongPositionUpdate,
)
from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.utils.callbacks import CallbackMixin


class SongPlayerLogic(CallbackMixin):
    """Bridges SongPlayerService results to the coordinator.

    Owns the RowSynthesizer and SongPlayerService. All playback controls are
    forwarded here from the UI panel. Position updates are forwarded to the
    coordinator via callbacks.
    """

    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        project_controller: ProjectController,
        config: Config,
    ) -> None:
        self._audio_device_manager = audio_device_manager
        self._project_controller = project_controller
        self._synthesizer = RowSynthesizer(project_controller, config)
        self._service = SongPlayerService(audio_device_manager, self._synthesizer)
        self._service.subscribe(self._on_service_result)
        self._audio_device_manager.on_acquire_output = self.stop
        self._audio_device_manager.external_output_priority = self._external_output_priority
        self._active_channels: FrozenSet[GeneratorName] = frozenset(GeneratorName.items())
        self._position = SongPosition()
        self._last_error: Optional[str] = None

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

    def stop(self) -> None:
        self._service.stop()
        self._position = SongPosition()
        self._emit_view()

    def is_playing(self) -> bool:
        return self._service.is_playing

    def is_paused(self) -> bool:
        return self._service.is_paused

    def is_loaded(self) -> bool:
        return self._project_controller.is_open

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
                self._position.order_position = position.order_position
                self._position.row_index = position.row_index
                self.call(self.on_position_changed, position.order_position, position.row_index)
                self._emit_view()
            case SongPlaybackStopped():
                self._emit_view()
            case SongPlaybackError(error=error):
                self._last_error = str(error) if str(error) else type(error).__name__
                self._position = SongPosition()
                self.call(self.on_error, error)
                self._emit_view()

    def _emit_view(self) -> None:
        self.call(self.on_view_changed, self._build_view_model())

    def _build_view_model(self) -> SongPlayerViewModel:
        return SongPlayerViewModel(
            is_loaded=self.is_loaded(),
            is_playing=self.is_playing(),
            is_paused=self.is_paused(),
            order_position=self._position.order_position,
            row_index=self._position.row_index,
            error=self._last_error,
        )
