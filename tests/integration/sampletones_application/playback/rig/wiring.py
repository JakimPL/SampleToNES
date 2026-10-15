from functools import partial
from pathlib import Path
from typing import Dict, Final, Optional

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.playback import AUDIO_TEARDOWN_SECONDS
from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.coordinators.playback.router import PlaybackRouter
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.audition import InstrumentAuditionLogic
from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.logic.sequencer.voices import SequencerVoicesLogic
from sampletones_application.logic.shared.audio_player import AudioPlayer
from sampletones_application.logic.shared.file_playback import FilePlayback
from sampletones_application.logic.shared.live import Keyboard, LiveKey, LiveKeysLogic, LiveSound, Strike
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.paths import LANG_EN
from sampletones_application.services.song_player.service import SongPlayerService
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.audio import AudioDeviceManager, DeviceCatalog
from sampletones_core.audio.driver import AudioDriverFactory
from sampletones_core.audio.output import AudioOutput, AudioSource, Playback, PlaybackListener
from sampletones_core.audio.output.source import ReportT
from sampletones_core.configs import Config
from sampletones_core.constants.audio import BufferSize, SampleRate
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.project.patterns.pitch import Note
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.constants.audio import UNITY_GAIN
from tests.conftest import RENDER_BUDGET
from tests.suite.audio.machine import FakeAudioSystem
from tests.suite.headless import profile_in
from tests.suite.regeneration import HeldRegeneration

from .editor import HeldInstrument
from .failures import RecordedFailures
from .hearing import Hearing
from .song import ScriptedSong
from .sound import Sound

VOICE_NAME: Final[str] = "lead"
KEYS_LINGER_SECONDS: Final[float] = 0.25
KEYS_CHANNEL: Final[ChannelName] = ChannelName.PULSE1


class HeardOutput(AudioOutput):
    """The application's audio output, with each playback's end report heard by the rig as its owner takes it."""

    def __init__(self, driver_factory: AudioDriverFactory, *, hearing: Hearing) -> None:
        super().__init__(driver_factory, post=CallbackQueue.add)
        self._hearing = hearing

    def play(
        self,
        source: AudioSource[ReportT],
        *,
        rank: int,
        listener: PlaybackListener[ReportT],
    ) -> Optional[Playback[ReportT]]:
        return super().play(source, rank=rank, listener=self._hearing.listening(listener))


class PlaybackStack:
    """Every object that sounds, wired as the composition root wires it, over one audio output on a fake machine.

    The reconstruction and instruction players, the song, the instrument's audition, the voice list, the
    file previews and the keys played live share the output, the previews and the keys through the one
    preview player, and the router reaches the three sources through the guards their tabs put in front of
    them. Each owner's marks and failures go to
    the hearing, the way each tab hands them to what it draws and to the failure presenter, and each owner
    is named to the hearing as the listener of its playbacks. The Audio settings verbs and the teardown
    reach the output the way the application's do.
    """

    def __init__(
        self,
        system: FakeAudioSystem,
        *,
        hearing: Hearing,
        profile: Path,
        scheduling: SchedulingBehavior,
    ) -> None:
        self.looping: bool = False
        self.active: Optional[Sound] = None
        self.file: Optional[Path] = None
        self.teardown_seconds: float = AUDIO_TEARDOWN_SECONDS

        self.output = HeardOutput(system.driver, hearing=hearing)
        self.manager = AudioDeviceManager(self.output.catalog)
        self.output.configure(self.manager.settings)
        self.preview_player = PreviewPlayer(self.output)
        self.language_manager = LanguageManager(LANG_EN)
        self.session_manager = SessionManager(profile_in(profile))
        self.controller = ProjectController(ProjectManager())
        self.controller.new()
        self.instrument: Instrument = self.controller.add_instrument(new_instrument(VOICE_NAME))
        self.previews = DocumentPreviews(RenderCache(budget_bytes=RENDER_BUDGET), HeldRegeneration())
        self.song = ScriptedSong([])

        self.reconstruction = self._player(Sound.RECONSTRUCTION, hearing)
        self.instruction = self._player(Sound.INSTRUCTION, hearing)
        self.song_service = SongPlayerService(
            self.output,
            self.song.synthesizer,
            should_loop=lambda: self.looping,
            master_gain=lambda: UNITY_GAIN,
            output_priority=PlaybackPriority.NORMAL,
        )
        hearing.owns(Sound.SONG, self.song_service)
        self.song_player = SongPlayerLogic(self.controller, self.session_manager, service=self.song_service)
        self.song_player.on_position_changed = hearing.rowed
        self.song_player.on_error = partial(hearing.tell, Sound.SONG)

        self.audition = InstrumentAuditionLogic(
            HeldInstrument(self.instrument),
            self.controller,
            self.session_manager,
            self.preview_player,
        )
        hearing.owns(Sound.AUDITION, self.audition)
        self.audition.on_position_changed = partial(hearing.marked, Sound.AUDITION)
        self.audition.on_audition_error = partial(hearing.tell, Sound.AUDITION)
        self.voices = SequencerVoicesLogic(
            self.controller,
            self.session_manager,
            self.preview_player,
            scheduling=scheduling,
            previews=self.previews,
        )
        hearing.owns(Sound.VOICE, self.voices)
        self.voices.on_autoplay_error = partial(hearing.tell, Sound.VOICE)
        self.files = FilePlayback(self.preview_player, self.previews)
        hearing.owns(Sound.FILE, self.files)
        self.files.on_error = partial(hearing.tell, Sound.FILE)
        self.keys_held: bool = False
        self.keys = LiveKeysLogic(
            self.preview_player,
            post=CallbackQueue.add,
            failed=partial(hearing.tell, Sound.KEYS),
            linger_seconds=KEYS_LINGER_SECONDS,
        )
        hearing.owns(Sound.KEYS, self.keys)

        self.guards: Dict[Sound, GuardedPlayer] = {
            Sound.RECONSTRUCTION: self._guarded(Sound.RECONSTRUCTION, self.reconstruction, hearing),
            Sound.INSTRUCTION: self._guarded(Sound.INSTRUCTION, self.instruction, hearing),
            Sound.SONG: self._guarded(Sound.SONG, self.song_player, hearing),
        }
        self.router = PlaybackRouter(
            sources=tuple(self.guards.values()),
            active_source_resolver=self._active_source,
            output=self.output,
            preview_player=self.preview_player,
            language_manager=self.language_manager,
            previews=self.previews,
        )

    def player(self, sound: Sound) -> PlayerLogic:
        match sound:
            case Sound.RECONSTRUCTION:
                return self.reconstruction
            case Sound.INSTRUCTION:
                return self.instruction
            case _:
                raise ValueError(f"The {sound.value} plays no buffer of its own")

    def strike(self, keyboard: Keyboard, number: int) -> Strike:
        """A press of key ``number`` on ``keyboard``, sounding the instrument at the note it names."""
        sound = LiveSound.of_voice(
            self.instrument,
            pitches={KEYS_CHANNEL: Note(value=number)},
            levels={KEYS_CHANNEL: MAX_VOLUME},
            config=Config(),
        )
        return Strike(key=LiveKey(keyboard=keyboard, number=number), sound=sound)

    def change_device(self, device_index: int, *, sample_rate: SampleRate) -> None:
        """Applies the Audio settings dialog's device and rate, as the application does."""
        self.manager.configure_device(device_index, sample_rate)
        self.output.configure(self.manager.settings)

    def set_buffer_size(self, frames: BufferSize) -> None:
        self.manager.set_buffer_size(frames)
        self.output.configure(self.manager.settings)

    def refresh(self) -> None:
        """The Audio settings dialog's Refresh, whose devices land on the render thread as the application's do."""
        self.output.refresh(self._refreshed)

    def teardown(self) -> None:
        """Quits the way the application does: every sound stops first, and the output closes at the end."""
        self.output.stop_all()
        self.output.close(deadline_seconds=self.teardown_seconds)

    def _refreshed(self, catalog: DeviceCatalog) -> None:
        self.manager.adopt(catalog)
        self.output.configure(self.manager.settings)

    def _player(self, sound: Sound, hearing: Hearing) -> PlayerLogic:
        audio_player = AudioPlayer(self.output)
        hearing.owns(sound, audio_player)
        player = PlayerLogic(audio_player)
        player.on_position_changed = partial(hearing.marked, sound)
        player.on_error = partial(hearing.tell, sound)
        return player

    def _guarded(
        self,
        sound: Sound,
        player: AudioPlayerProtocol,
        hearing: Hearing,
    ) -> GuardedPlayer:
        return GuardedPlayer(
            player,
            failures=RecordedFailures(hearing.tell, listener=sound, language_manager=self.language_manager),
            previews=self.previews,
        )

    def _active_source(self) -> Optional[GuardedPlayer]:
        if self.active is None:
            return None

        return self.guards.get(self.active)
