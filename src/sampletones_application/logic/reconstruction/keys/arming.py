from typing import Callable, Optional, Tuple

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.audition import InstrumentAuditionLogic
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.editing import InstrumentAuditionProtocol
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.performance import VoiceReading, heard_readings
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample

from .armed import ArmedVoice

Inputs = Tuple[object, ...]
Build = Callable[[], Optional[ArmedVoice]]


class KeyArming:
    """Keeps what a key sounds on the Reconstructions tab in step with the voice the tab shows.

    The tab's voice is the render thread's to read, so the render thread arms the keys once a frame. It
    compares what the voice and the settings a key is read under are made of with what it armed last, and
    builds a new :class:`ArmedVoice` only where they differ. An edit puts a new object in place of the one
    it changed, a recording or an instrument's envelopes, so an object is compared by identity, and the
    reader's hearing and the settings by value. The keys of either keyboard read the voice armed last, whole,
    from the thread they arrive on.

    An instrument is armed on the channel it is auditioned on, at the project's rates, from a copy the tab's
    edits leave as it is. A recording is armed as the reader hears it, at the rates it was converted at.
    """

    def __init__(
        self,
        editor: InstrumentAuditionProtocol,
        audition: InstrumentAuditionLogic,
        reconstructions: ReconstructionManager,
        project_controller: ProjectController,
        session_manager: SessionManager,
        *,
        sample_root: int,
    ) -> None:
        """Holds where the voice and the settings a key reads come from.

        Args:
            editor: Where the instrument in front of the tab comes from.
            audition: The generator the instrument is auditioned on.
            reconstructions: The recording in front of the tab, and what the reader hears of it.
            project_controller: The rates an instrument is synthesized at.
            session_manager: Whether a MIDI key's velocity sets the volume.
            sample_root: The key playing a recording as it was recorded.
        """
        self._editor = editor
        self._audition = audition
        self._reconstructions = reconstructions
        self._controller = project_controller
        self._session_manager = session_manager
        self._sample_root = sample_root
        self._inputs: Optional[Inputs] = None
        self._anchors: Tuple[object, ...] = ()
        self._armed: Optional[ArmedVoice] = None

    @property
    def armed(self) -> Optional[ArmedVoice]:
        """What a key sounds now, or ``None`` while the tab shows no voice a key can sound."""
        return self._armed

    def arm(self) -> None:
        """Builds what a key sounds where the voice or its settings changed since the last arming."""
        instrument = self._editor.instrument
        if instrument is not None:
            self._arm_instrument(instrument)
            return

        data = self._reconstructions.current_reconstruction
        if data is not None:
            self._arm_recording(data)
            return

        self._settle((), (), lambda: None)

    def _arm_instrument(self, instrument: Instrument) -> None:
        settings = self._controller.project.settings
        channel_name = self._audition.channel_name
        inputs: Inputs = (
            VoiceKind.INSTRUMENT,
            id(instrument),
            id(instrument.envelopes),
            instrument.initial_pitch,
            instrument.initial_period,
            channel_name,
            settings.nes_frequency,
            settings.sample_rate,
            self._session_manager.velocity_sets_volume,
        )

        def build() -> Optional[ArmedVoice]:
            snapshot = instrument.snapshot()
            reading = VoiceReading.read(snapshot, channel_name)
            if reading is None:
                return None

            return ArmedVoice(
                voice_id=snapshot.id,
                kind=VoiceKind.INSTRUMENT,
                readings={channel_name: reading},
                config=settings.synthesis_config(),
                sample_root=self._sample_root,
                velocity_sets_volume=self._session_manager.velocity_sets_volume,
            )

        self._settle(inputs, (instrument, instrument.envelopes), build)

    def _arm_recording(self, data: ReconstructionData) -> None:
        hearing = self._reconstructions.listening.hearing
        reconstruction = data.reconstruction
        inputs: Inputs = (
            VoiceKind.SAMPLE,
            id(reconstruction),
            hearing,
            self._session_manager.velocity_sets_volume,
        )

        def build() -> Optional[ArmedVoice]:
            sample = Sample(name=data.name, reconstruction=reconstruction)
            readings = heard_readings(sample, hearing)
            if not readings:
                return None

            return ArmedVoice(
                voice_id=sample.id,
                kind=VoiceKind.SAMPLE,
                readings=readings,
                config=reconstruction.config,
                sample_root=self._sample_root,
                velocity_sets_volume=self._session_manager.velocity_sets_volume,
            )

        self._settle(inputs, (reconstruction,), build)

    def _settle(self, inputs: Inputs, anchors: Tuple[object, ...], build: Build) -> None:
        """Arms what ``build`` makes where ``inputs`` differ from the last arming's.

        The objects compared by identity are kept in ``anchors`` until the next change, so an identity
        compared stays theirs alone.
        """
        if inputs == self._inputs:
            return

        self._armed = build()
        self._inputs = inputs
        self._anchors = anchors
