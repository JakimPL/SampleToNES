from functools import partial
from pathlib import Path
from typing import Dict, Final, Optional

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.coordinators.playback.router import PlaybackRouter
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.audition import InstrumentAuditionLogic
from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.logic.sequencer.voices import SequencerVoicesLogic
from sampletones_application.logic.shared.file_playback import FilePlayback
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.paths import LANG_EN
from sampletones_application.services.song_player.service import SongPlayerService
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.audio import AudioDeviceManager
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


class PlaybackStack:
    """Every object that sounds, wired as the composition root wires it, over one device manager on a fake machine.

    The reconstruction and instruction players, the song, the instrument's audition, the voice list and the
    file previews share the manager, and the router reaches the three sources through the guards their tabs
    put in front of them. Each owner's reports and failures go to the hearing, the way each tab hands them to
    what it draws and to the failure presenter. The device's own error hook crosses to the render thread
    before it is told, as the application's does.
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
        self.gain: float = UNITY_GAIN
        self.active: Optional[Sound] = None
        self.file: Optional[Path] = None

        self.manager = AudioDeviceManager(system.driver)
        self.manager.set_callbacks(on_playback_error=partial(CallbackQueue.add, hearing.tell, None))
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
            self.manager,
            self.song,
            should_loop=lambda: self.looping,
            master_gain=lambda: self.gain,
            output_priority=PlaybackPriority.NORMAL,
        )
        self.song_player = SongPlayerLogic(self.controller, self.session_manager, service=self.song_service)
        self.song_player.on_position_changed = hearing.rowed
        self.song_player.on_error = partial(hearing.tell, Sound.SONG)
        self.song_service.subscribe(hearing.song_result)

        self.audition = InstrumentAuditionLogic(
            HeldInstrument(self.instrument),
            self.controller,
            self.session_manager,
            self.manager,
        )
        self.audition.on_position_changed = hearing.auditioned
        self.audition.on_audition_error = partial(hearing.tell, Sound.AUDITION)
        self.voices = SequencerVoicesLogic(
            self.controller,
            self.session_manager,
            self.manager,
            scheduling=scheduling,
            previews=self.previews,
        )
        self.voices.on_autoplay_error = partial(hearing.tell, Sound.VOICE)
        self.files = FilePlayback(self.manager, self.previews)
        self.files.on_error = partial(hearing.tell, Sound.FILE)

        self.guards: Dict[Sound, GuardedPlayer] = {
            Sound.RECONSTRUCTION: self._guarded(Sound.RECONSTRUCTION, self.reconstruction, hearing),
            Sound.INSTRUCTION: self._guarded(Sound.INSTRUCTION, self.instruction, hearing),
            Sound.SONG: self._guarded(Sound.SONG, self.song_player, hearing),
        }
        self.router = PlaybackRouter(
            sources=tuple(self.guards.values()),
            active_source_resolver=self._active_source,
            audio_device_manager=self.manager,
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

    def _player(self, sound: Sound, hearing: Hearing) -> PlayerLogic:
        player = PlayerLogic(self.manager, partial(hearing.notified, sound))
        player.on_position_changed = partial(hearing.marked, sound)
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
