from typing import Callable, Optional

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.sequencer.samples import (
    SampleEntryViewModel,
    SequencerSamplesViewModel,
)
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.formats.famitracker.footprint import reconstruction_footprints
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.utils.display import display_voice
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

        self.on_voices_changed: Optional[Callable[[SequencerSamplesViewModel], None]] = None
        self.on_edit_sample_requested: Optional[StringCallback] = None
        self.on_autoplay_error: Optional[Callable[[Exception], None]] = None

    def build_samples(self) -> SequencerSamplesViewModel:
        entries = tuple(
            SampleEntryViewModel(
                voice_id=sample.id,
                name=sample.name,
                loop=sample.loops,
            )
            for sample in self._controller.project.voices
        )
        return SequencerSamplesViewModel(samples=entries)

    def push_samples(self) -> None:
        self.call(self.on_voices_changed, self.build_samples())

    def add_sample(self, reconstruction: Reconstruction, name: str) -> Sample:
        return self._controller.add_sample(reconstruction, name)

    def rename_voice(self, voice_id: str, name: str) -> None:
        self._controller.rename_voice(voice_id, name)

    def is_voice_used(self, voice_id: str) -> bool:
        return self._controller.is_voice_used(voice_id)

    def build_sample_footprint(self, voice_id: str) -> Optional[SampleFootprintViewModel]:
        """Measures one sample's instruments as the module export writes them.

        A sample carries its own loop flag, and a looping instrument is compiled to the shortest
        length its envelopes share, so the sample is measured the way it is placed. Measuring a
        single sample on demand keeps a pool edit clear of an export it was not asked for.

        Args:
            voice_id: The sample to measure.

        Returns:
            Optional[SampleFootprintViewModel]: The sample's byte figures, or ``None`` while the
            pool holds no such sample.
        """
        sample = self._controller.project.voices.get(voice_id)
        if not isinstance(sample, Sample):
            return None

        return SampleFootprintViewModel.from_footprints(
            reconstruction_footprints(sample.reconstruction, loop=sample.loops)
        )

    def sample_name(self, voice_id: str) -> str:
        return self._controller.project.voices[voice_id].name

    def sample_position(self, voice_id: str) -> str:
        """Returns the sample's hex list position, matching how the tracker labels it."""
        return display_voice(
            voices=self._controller.project.voices,
            voice_id=voice_id,
        )

    def remove_voice(self, voice_id: str) -> None:
        self._controller.remove_voice(voice_id)

    def move_voice(self, voice_id: str, to_index: int) -> None:
        self._controller.move_voice(voice_id, to_index)

    def duplicate_voice(self, voice_id: str) -> None:
        self._controller.duplicate_voice(voice_id)

    def set_sample_loop(self, voice_id: str, loop: bool) -> None:
        """Turns the list's loop tick into the point the voice repeats from.

        The list offers looping as a switch, and a voice that loops repeats the whole of its
        instructions, which is the point at their start.
        """
        self._controller.set_voice_loop_point(voice_id, WHOLE_LOOP_POINT if loop else None)

    def request_edit(self, voice_id: str) -> None:
        self.cancel_autoplay()
        self.call(self.on_edit_sample_requested, voice_id)

    def play_sample(self, voice_id: str) -> None:
        """Plays a sample on demand, regardless of the autoplay setting.

        Explicit playback is intentional, so it uses ``NORMAL`` priority and thereby
        preempts the sequencer song / reconstruction players.
        """
        self._play_sample(voice_id, priority=PlaybackPriority.NORMAL)

    def request_autoplay(self, voice_id: str) -> None:
        """Schedules a debounced preview that a following double-click can cancel."""
        self._pending_autoplay_sample = voice_id
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

        voice_id = self._pending_autoplay_sample
        self._pending_autoplay_sample = None
        if self._session_manager.autoplay:
            self._play_sample(voice_id, priority=PlaybackPriority.PREVIEW)

    def _play_sample(
        self,
        voice_id: str,
        *,
        priority: PlaybackPriority,
    ) -> None:
        sample = self._controller.project.voices.get(voice_id)
        if not isinstance(sample, Sample):
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
                f"Failed to preview sample: {voice_id}",
            )
            self.call(self.on_autoplay_error, exception)
