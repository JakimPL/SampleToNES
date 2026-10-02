from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Protocol, Tuple

from sampletones_application.config.managers.application import ApplicationConfigManager
from sampletones_application.config.managers.state import ApplicationStateManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.config.session.state.window import ViewportState
from sampletones_core.configs import Config
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT
from sampletones_shared.paths.user import CONFIG_PATH, PROJECTS_DIRECTORY, RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.environment import SCREEN_SIZE
from tests.suite.screens.seeds import (
    ArrangedProject,
    LongEnvelopeProject,
    MiniLibrary,
    OverlongProject,
    PlayableReconstruction,
    Recording,
    ReleasingInstrumentFile,
    StoredProject,
    StoredReconstruction,
    TwoTuningsProject,
    stored_recording,
)

OPEN_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Open.stn"
OTHER_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Other.stn"
SONG: Final[Path] = PROJECTS_DIRECTORY / "Song.stp"
SONG_SAMPLE: Final[str] = "Lead"
SONG_INSTRUMENT: Final[str] = "Pad"
BASS: Final[str] = "bass.wav"
LEAD: Final[str] = "lead.wav"
DOCUMENT_RECORDING_SECONDS: Final[float] = 0.3
DOCUMENT_RECORDING_FREQUENCY: Final[float] = 220.0
PLAYABLE_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Playable.stn"
SECOND_PLAYABLE: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Second.stn"
STEMS_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Stems.stn"
SHORT_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Short.stn"
TAKES: Final[Tuple[str, ...]] = ("take1.wav", "take2.wav", "take3.wav")
STEM_TAKES: Final[Tuple[str, ...]] = ("stem1.wav", "stem2.wav", "stem3.wav")
STEM_FRAMES: Final[int] = 60
PLAYABLE_FRAMES: Final[int] = 600
FRAMES_PER_SECOND: Final[int] = 60
ARRANGED_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Arranged.stp"
LINE: Final[str] = "Line"
BASS_VOICE: Final[str] = "Bass"
PAD: Final[str] = "Pad"
PAD_ROW: Final[int] = 4
BASS_ROW: Final[int] = 8
TAKE_FREQUENCY: Final[float] = 220.0
SINGLE_ORDER_FRAME: Final[int] = 1
LOOPING_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Looping.stp"
LOOPING_ORDER_FRAMES: Final[int] = 2
OVERLONG_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Overlong.stp"
OVERLONG_SAMPLE: Final[str] = "Turning"
OVERLONG_ORDER_FRAMES: Final[int] = 12
TWO_TUNINGS_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Tunings.stp"
RETUNED_A4: Final[float] = 432.0
LONG_ENVELOPES_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Envelopes.stp"
LONG_VOICE: Final[str] = "Long"
LONG_ITEMS: Final[int] = 600
MIDDLING_VOICE: Final[str] = "Middling"
MIDDLING_ITEMS: Final[int] = 300
INSTRUMENTS_FOLDER: Final[str] = "instruments"
RELEASING_INSTRUMENT: Final[str] = "Releasing"


class HomeFile(Protocol):
    """Something a scenario's home holds before the application starts: a recording, a document, a library."""

    def write(self) -> None:
        """Writes it under the home of the scenario's process."""


@dataclass(frozen=True)
class World:
    """What a scenario's home holds before the application draws its first frame.

    Each file is written by the same model and the same manager the application reads it with, so
    a home seeded here is a home a previous run could have left.

    Attributes:
        state: The session the application restores, or ``None`` for a home no run has left one in.
        application_config: The application's settings, or ``None`` for a home holding none.
        config: The reconstruction settings in the documents folder, or ``None`` for a home holding none.
        files: Everything else the home holds.
    """

    state: Optional[ApplicationState]
    application_config: Optional[ApplicationConfig]
    config: Optional[Config]
    files: Tuple[HomeFile, ...]

    def write(self, profile: UserProfile) -> None:
        """Lays the world out in the home ``profile`` reads its settings from."""
        if self.state is not None:
            state_manager = ApplicationStateManager(profile.state)
            state_manager.state = self.state
            state_manager.save()

        if self.application_config is not None:
            config_manager = ApplicationConfigManager(profile.config)
            config_manager.config = self.application_config
            config_manager.save()

        if self.config is not None:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.config.save(CONFIG_PATH)

        for file in self.files:
            file.write()


def screen_filling_state() -> ApplicationState:
    """A session whose window spans the scenario's screen, which the application fits within its margins."""
    return ApplicationState(
        viewport=ViewportState(
            width=SCREEN_SIZE.width,
            height=SCREEN_SIZE.height,
            x=0,
            y=0,
        )
    )


def one_worker_config() -> Config:
    """Reconstruction settings running one job at a time, which keeps a scenario's run on a worker of its own."""
    config = Config()
    general = config.general.model_copy(update={"max_workers": 1})
    return config.model_copy(update={"general": general})


def converting_world(files: Tuple[HomeFile, ...]) -> World:
    """A home ready to convert: one-worker settings, a small library built for them, and ``files``."""
    config = one_worker_config()
    return World(
        state=screen_filling_state(),
        application_config=None,
        config=config,
        files=(MiniLibrary(config), *files),
    )


def lived_in_world() -> World:
    """The home of a user who ran the application once: a session left behind, and nothing else."""
    return World(
        state=screen_filling_state(),
        application_config=None,
        config=None,
        files=(),
    )


def documents_world() -> World:
    """A home ready to convert that holds the documents a user puts away and replaces.

    It holds two reconstructions, :data:`OPEN_RECONSTRUCTION` and :data:`OTHER_RECONSTRUCTION`,
    with the recording they name; the project :data:`SONG` with a sample and an instrument; and
    two recordings to convert, :data:`BASS` and :data:`LEAD`, in the home itself.
    """
    recordings = tuple(
        Recording(
            destination=Path.cwd() / name,
            seconds=DOCUMENT_RECORDING_SECONDS,
            frequency=DOCUMENT_RECORDING_FREQUENCY,
        )
        for name in (BASS, LEAD)
    )
    return converting_world(
        (
            *recordings,
            StoredReconstruction(OPEN_RECONSTRUCTION),
            StoredReconstruction(OTHER_RECONSTRUCTION),
            stored_recording(),
            StoredProject(SONG, sample=SONG_SAMPLE, instrument=SONG_INSTRUMENT),
        )
    )


def playing_world() -> World:
    """A home holding reconstructions that play: two of one recording each, and one of three recordings in turn.

    :data:`PLAYABLE_RECONSTRUCTION` and :data:`SECOND_PLAYABLE` play the first and the second of
    :data:`TAKES`, the shorter :data:`STEMS_RECONSTRUCTION` plays the three :data:`STEM_TAKES` in
    turn, and :data:`SHORT_RECONSTRUCTION` plays the first of them alone. The home holds the stored
    :data:`OPEN_RECONSTRUCTION`, sounding every channel, and the project :data:`SONG` besides.
    """
    takes = tuple(Path.cwd() / name for name in TAKES)
    stem_takes = tuple(Path.cwd() / name for name in STEM_TAKES)
    recordings = tuple(
        Recording(destination=take, seconds=frames / FRAMES_PER_SECOND, frequency=TAKE_FREQUENCY * (index + 1))
        for paths, frames in ((takes, PLAYABLE_FRAMES), (stem_takes, STEM_FRAMES))
        for index, take in enumerate(paths)
    )
    return World(
        state=screen_filling_state(),
        application_config=None,
        config=None,
        files=(
            *recordings,
            PlayableReconstruction(PLAYABLE_RECONSTRUCTION, takes[:1], PLAYABLE_FRAMES),
            PlayableReconstruction(SECOND_PLAYABLE, takes[1:2], PLAYABLE_FRAMES),
            PlayableReconstruction(STEMS_RECONSTRUCTION, stem_takes, STEM_FRAMES),
            PlayableReconstruction(SHORT_RECONSTRUCTION, stem_takes[:1], STEM_FRAMES),
            StoredReconstruction(OPEN_RECONSTRUCTION),
            stored_recording(),
            StoredProject(SONG, sample=SONG_SAMPLE, instrument=SONG_INSTRUMENT),
        ),
    )


def sequencer_world() -> World:
    """A home holding :data:`ARRANGED_PROJECT`, its voices placed on its first pattern, and the playing world's files.

    The project's sample :data:`LINE` starts the pattern on Pulse 1, its hand-written :data:`PAD`
    comes in on Pulse 2 at :data:`PAD_ROW`, and its sample :data:`BASS_VOICE` on the triangle at
    :data:`BASS_ROW`.
    """
    playing = playing_world()
    return World(
        state=playing.state,
        application_config=None,
        config=None,
        files=(
            *playing.files,
            arranged_project(ARRANGED_PROJECT, SINGLE_ORDER_FRAME),
        ),
    )


def exporting_world() -> World:
    """The sequencer's home, holding besides the projects an export meets at its limits.

    :data:`LOOPING_PROJECT` is :data:`ARRANGED_PROJECT` with its pattern played twice in the order.
    :data:`OVERLONG_PROJECT` changes every channel at every tick through :data:`OVERLONG_ORDER_FRAMES`
    frames. :data:`TWO_TUNINGS_PROJECT` holds :data:`LINE` at the default tuning and
    :data:`BASS_VOICE` with A4 at :data:`RETUNED_A4` hertz. :data:`LONG_ENVELOPES_PROJECT` holds
    :data:`LONG_VOICE` and :data:`MIDDLING_VOICE`, whose volume envelopes run :data:`LONG_ITEMS` and
    :data:`MIDDLING_ITEMS` items. The home's :data:`INSTRUMENTS_FOLDER` holds the FamiTracker instrument
    :data:`RELEASING_INSTRUMENT`, whose volume states a release point.
    """
    sequencer = sequencer_world()
    return World(
        state=sequencer.state,
        application_config=None,
        config=None,
        files=(
            *sequencer.files,
            arranged_project(LOOPING_PROJECT, LOOPING_ORDER_FRAMES),
            OverlongProject(OVERLONG_PROJECT, sample=OVERLONG_SAMPLE, order_frames=OVERLONG_ORDER_FRAMES),
            TwoTuningsProject(TWO_TUNINGS_PROJECT, line=LINE, bass=BASS_VOICE, a4_frequency=RETUNED_A4),
            LongEnvelopeProject(
                LONG_ENVELOPES_PROJECT,
                long=LONG_VOICE,
                long_items=LONG_ITEMS,
                middling=MIDDLING_VOICE,
                middling_items=MIDDLING_ITEMS,
            ),
            ReleasingInstrumentFile(releasing_instrument(), name=RELEASING_INSTRUMENT),
        ),
    )


def releasing_instrument() -> Path:
    """Where the home holds the FamiTracker instrument :data:`RELEASING_INSTRUMENT`."""
    return Path.cwd() / INSTRUMENTS_FOLDER / f"{RELEASING_INSTRUMENT}{EXT_FILE_INSTRUMENT}"


def arranged_project(destination: Path, order_frames: int) -> ArrangedProject:
    """The arranged project laid at ``destination``, its pattern played ``order_frames`` times in the order."""
    return ArrangedProject(
        destination,
        line=LINE,
        bass=BASS_VOICE,
        pad=PAD,
        pad_row=PAD_ROW,
        bass_row=BASS_ROW,
        order_frames=order_frames,
    )
