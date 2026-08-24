from pathlib import Path
from typing import Callable, Final, Optional, Tuple

import numpy as np

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.sequencer.kind import voice_kind
from sampletones_application.view_model.sequencer.voices import (
    SequencerVoicesViewModel,
    VoiceEntryViewModel,
    VoiceKind,
)
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.slices import VoiceSlice, sample_slices
from sampletones_core.formats.famitracker.footprint import (
    features_footprint,
    reconstruction_footprints,
)
from sampletones_core.formats.famitracker.instrument import read_fti
from sampletones_core.formats.famitracker.voice import (
    ImportedVoice,
    instrument_to_voice,
)
from sampletones_core.generators.render import render_instructions
from sampletones_core.project.voices.creation import (
    instrument_from_features,
    new_instrument,
)
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.utils.display import display_voice
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import StringCallback
from sampletones_shared.utils.callbacks import CallbackMixin

PREVIEW_CHANNEL: Final[ChannelName] = ChannelName.PULSE1


class SequencerVoicesLogic(CallbackMixin):
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

        self.on_voices_changed: Optional[Callable[[SequencerVoicesViewModel], None]] = None
        self.on_edit_sample_requested: Optional[StringCallback] = None
        self.on_autoplay_error: Optional[Callable[[Exception], None]] = None

    def build_voices(self) -> SequencerVoicesViewModel:
        entries = tuple(
            VoiceEntryViewModel(
                voice_id=voice.id,
                name=voice.name,
                kind=voice_kind(voice),
                loop=_loops(voice),
            )
            for voice in self._controller.project.voices
        )
        return SequencerVoicesViewModel(voices=entries)

    def push_voices(self) -> None:
        self.call(self.on_voices_changed, self.build_voices())

    def add_sample(self, reconstruction: Reconstruction, name: str) -> Sample:
        return self._controller.add_sample(reconstruction, name)

    def add_new_instrument(self, name: str) -> Instrument:
        """Writes a fresh instrument into the pool, sustaining until its envelopes are edited."""
        return self.add_instrument(new_instrument(name))

    def add_instrument(self, instrument: Instrument) -> Instrument:
        """Takes a whole instrument voice into the pool, whichever route made it."""
        return self._controller.add_instrument(instrument)

    def read_instrument(self, filepath: Path) -> ImportedVoice:
        """Reads a FamiTracker instrument file as a voice, leaving the pool as it stands.

        The file states the name the voice takes, and a file naming nothing leaves the voice
        named after the file itself, so the list states where every voice came from.

        Args:
            filepath: The ``.fti`` file the voice is read from.

        Returns:
            ImportedVoice: The voice the file describes, beside what the file stated past it.

        Raises:
            FileNotFoundError: If no file stands at ``filepath``.
            LoadInstrumentError: If the file departs from the instrument layout.
        """
        imported = instrument_to_voice(read_fti(filepath))
        if not imported.voice.name:
            imported.voice.name = filepath.stem

        return imported

    def instrument_channels(self, voice_id: str) -> Tuple[ChannelName, ...]:
        """The channels of one voice a new instrument can be written from.

        A recording's channel carries frames of its own, so each of them makes a voice of
        envelopes the reader edits directly. A voice written by hand already is that, so it offers
        none and the menu says so.

        Args:
            voice_id: The voice a new instrument would be taken from.

        Returns:
            Tuple[ChannelName, ...]: The channels it offers, in channel order.
        """
        return tuple(voice_slice.channel for voice_slice in self._channel_slices(voice_id))

    def instrument_from_channel(
        self,
        voice_id: str,
        channel_name: ChannelName,
    ) -> Optional[Instrument]:
        """Writes what one channel of a voice plays into an instrument, leaving the pool as it stands.

        The new voice carries the channel's envelopes and the reference they were measured
        against, and it is named after the channel it came from, so the list says where it came
        from the way an exported slice does.

        Args:
            voice_id: The voice the channel belongs to.
            channel_name: The channel whose envelopes the instrument takes.

        Returns:
            Optional[Instrument]: The voice those envelopes describe, or ``None`` where the pool
            holds no such voice or it plays nothing on that channel.
        """
        voice_slice = next(
            (candidate for candidate in self._channel_slices(voice_id) if candidate.channel is channel_name),
            None,
        )
        if voice_slice is None:
            return None

        return instrument_from_features(
            voice_slice.instrument_name,
            voice_slice.features,
            channel_name,
        )

    def _channel_slices(self, voice_id: str) -> Tuple[VoiceSlice, ...]:
        """What each channel of a recording plays, which is what an instrument is written from."""
        match self._controller.project.voices.get(voice_id):
            case Sample() as sample:
                return tuple(sample_slices(sample))
            case _:
                return ()

    def rename_voice(self, voice_id: str, name: str) -> None:
        self._controller.rename_voice(voice_id, name)

    def is_voice_used(self, voice_id: str) -> bool:
        return self._controller.is_voice_used(voice_id)

    def build_voice_footprint(
        self,
        voice_id: str,
    ) -> Optional[SampleFootprintViewModel]:
        """Measures one voice's instruments as the module export writes them.

        A voice carries its own loop point, and a looping instrument is compiled to one shared
        length, so it is measured the way it is placed. A sample yields a figure per channel its
        reconstruction covers; an instrument yields one, since every channel reaches the same
        envelopes. Measuring a single voice on demand keeps a pool edit clear of an export it was
        not asked for.

        Args:
            voice_id: The voice to measure.

        Returns:
            Optional[SampleFootprintViewModel]: The voice's byte figures, or ``None`` while the
            pool holds no such voice.
        """
        match self._controller.project.voices.get(voice_id):
            case Sample() as sample:
                return SampleFootprintViewModel.from_footprints(reconstruction_footprints(sample.reconstruction))
            case Instrument() as instrument:
                return SampleFootprintViewModel.from_instrument(features_footprint(instrument.instrument_features()))
            case _:
                return None

    def voice_name(self, voice_id: str) -> str:
        return self._controller.project.voices[voice_id].name

    def voice_position(self, voice_id: str) -> str:
        """Returns the sample's hex list position, matching how the tracker labels it."""
        return display_voice(
            voices=self._controller.project.voices,
            voice_id=voice_id,
        )

    def voice_kind(self, voice_id: str) -> Optional[VoiceKind]:
        """Which of the two kinds a voice in the pool is, telling a recording from a written one.

        Args:
            voice_id: The voice being asked about.

        Returns:
            Optional[VoiceKind]: The kind the pool holds it as, or ``None`` while the pool holds
            no such voice.
        """
        voice = self._controller.project.voices.get(voice_id)
        if voice is None:
            return None

        return voice_kind(voice)

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

    def play_voice(self, voice_id: str) -> None:
        """Plays a sample on demand, regardless of the autoplay setting.

        Explicit playback is intentional, so it uses ``NORMAL`` priority and thereby
        preempts the sequencer song / reconstruction players.
        """
        self._play_voice(voice_id, priority=PlaybackPriority.NORMAL)

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
            self._play_voice(voice_id, priority=PlaybackPriority.PREVIEW)

    def _preview_audio(self, voice_id: str) -> Optional[np.ndarray]:
        """The audio a preview sounds: a sample's approximation, or an instrument rendered on the pulse.

        The pulse channel offers every dimension an instrument writes, so rendering the preview there
        sounds the whole instrument rather than the part another channel would read.

        Args:
            voice_id: The voice to preview.

        Returns:
            Optional[np.ndarray]: The waveform to play, or ``None`` where the voice sounds nothing.
        """
        match self._controller.project.voices.get(voice_id):
            case Sample() as sample:
                return sample.reconstruction.approximation
            case Instrument() as instrument:
                instructions = instrument.instructions(PREVIEW_CHANNEL)
                if not instructions:
                    return None

                return render_instructions(
                    instructions,
                    PREVIEW_CHANNEL,
                    self._preview_config(),
                )
            case _:
                return None

    def _preview_config(self) -> Config:
        settings = self._controller.project.settings
        return Config().with_library(
            nes_frequency=settings.nes_frequency,
            sample_rate=settings.sample_rate,
        )

    def _play_voice(
        self,
        voice_id: str,
        *,
        priority: PlaybackPriority,
    ) -> None:
        audio = self._preview_audio(voice_id)
        if audio is None:
            return

        try:
            self._audio_device_manager.play(
                audio,
                update=False,
                priority=priority,
            )
        except (PlaybackError, ValueError) as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to preview sample: {voice_id}",
            )
            self.call(self.on_autoplay_error, exception)


def _loops(voice: VoiceUnion) -> bool:
    """Whether the voice list marks this voice as repeating.

    A recording states one point for the whole of it, while a hand-written voice repeats wherever
    any of its dimensions circles.
    """
    if isinstance(voice, Sample):
        return voice.loops

    return any(envelope.loops for envelope in voice.envelopes.envelope_map.values())
