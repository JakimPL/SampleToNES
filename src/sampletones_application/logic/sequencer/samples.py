from typing import Callable, Optional

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.sequencer.samples import (
    SampleEntryViewModel,
    SequencerSamplesViewModel,
)
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.utils.display import display_sample
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import StringCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerSamplesLogic(CallbackMixin):
    """Drives the samples panel: lists the pool, edits it, and previews samples.

    Every pool edit goes through the controller so the project stays the single
    source of truth. ``on_edit_sample_requested`` hands a sample id to the
    application, which opens that sample's reconstruction in the Reconstruction
    tab for live-linked editing.

    Previewing mirrors the reconstruction browser: a single click schedules a
    debounced autoplay that fires only when the session's autoplay flag is on, and
    a double-click (edit) cancels the pending preview before it plays.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        *,
        scheduling: SchedulingBehavior,
    ) -> None:
        self._controller = project_controller
        self._session_manager = session_manager
        self._audio_device_manager = audio_device_manager
        self._scheduling = scheduling
        self._pending_autoplay_sample: Optional[str] = None

        self.on_samples_changed: Optional[Callable[[SequencerSamplesViewModel], None]] = None
        self.on_edit_sample_requested: Optional[StringCallback] = None
        self.on_autoplay_error: Optional[Callable[[Exception], None]] = None

    def build_samples(self) -> SequencerSamplesViewModel:
        entries = tuple(
            SampleEntryViewModel(
                sample_id=sample.id,
                name=sample.name,
                loop=sample.loop,
            )
            for sample in self._controller.project.samples
        )
        return SequencerSamplesViewModel(samples=entries)

    def push_samples(self) -> None:
        self.call(self.on_samples_changed, self.build_samples())

    def add_sample(self, reconstruction: Reconstruction, name: str) -> Sample:
        return self._controller.add_sample(reconstruction, name)

    def rename_sample(self, sample_id: str, name: str) -> None:
        self._controller.rename_sample(sample_id, name)

    def is_sample_used(self, sample_id: str) -> bool:
        return self._controller.is_sample_used(sample_id)

    def sample_name(self, sample_id: str) -> str:
        return self._controller.project.samples[sample_id].name

    def sample_position(self, sample_id: str) -> str:
        """Returns the sample's hex list position, matching how the tracker labels it."""
        return display_sample(samples=self._controller.project.samples, sample_id=sample_id)

    def remove_sample(self, sample_id: str) -> None:
        self._controller.remove_sample(sample_id)

    def move_sample(self, sample_id: str, to_index: int) -> None:
        self._controller.move_sample(sample_id, to_index)

    def duplicate_sample(self, sample_id: str) -> None:
        self._controller.duplicate_sample(sample_id)

    def set_sample_loop(self, sample_id: str, loop: bool) -> None:
        self._controller.set_sample_loop(sample_id, loop)

    def request_edit(self, sample_id: str) -> None:
        self.cancel_autoplay()
        self.call(self.on_edit_sample_requested, sample_id)

    def play_sample(self, sample_id: str) -> None:
        """Plays a sample on demand, regardless of the autoplay setting.

        Explicit playback is intentional, so it uses ``NORMAL`` priority and thereby
        preempts the sequencer song / reconstruction players.
        """
        self._play_sample(sample_id, priority=PlaybackPriority.NORMAL)

    def request_autoplay(self, sample_id: str) -> None:
        """Schedules a debounced preview that a following double-click can cancel."""
        self._pending_autoplay_sample = sample_id
        CallbackQueue.add(
            self._execute_autoplay,
            priority=self._scheduling.priorities.schedule,
            delay=self._scheduling.delays.schedule,
        )

    def cancel_autoplay(self) -> None:
        self._pending_autoplay_sample = None

    def _execute_autoplay(self) -> None:
        if self._pending_autoplay_sample is None:
            return

        sample_id = self._pending_autoplay_sample
        self._pending_autoplay_sample = None
        if self._session_manager.autoplay:
            self._play_sample(sample_id, priority=PlaybackPriority.PREVIEW)

    def _play_sample(self, sample_id: str, *, priority: PlaybackPriority) -> None:
        sample = self._controller.project.samples.get(sample_id)
        if sample is None:
            return

        try:
            self._audio_device_manager.play(
                sample.reconstruction.approximation,
                update=False,
                priority=priority,
            )
        except (PlaybackError, ValueError) as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to preview sample: {sample_id}",
            )
            self.call(self.on_autoplay_error, exception)
