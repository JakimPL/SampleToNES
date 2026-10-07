from pathlib import Path
from typing import Final, Tuple

from sampletones_shared.constants.nes import DEFAULT_NES_FREQUENCY
from sampletones_shared.paths.user import PROJECTS_DIRECTORY, RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.seeds.libraries import MiniLibrary
from tests.suite.screens.seeds.projects import StoredProject
from tests.suite.screens.seeds.reconstructions import PlayableReconstruction, StoredReconstruction
from tests.suite.screens.seeds.recordings import Recording, stored_recording
from tests.suite.screens.worlds.home import HomeFile, World, one_worker_config, screen_filling_state

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
TAKE_FREQUENCY: Final[float] = 220.0


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
    """A home holding reconstructions that play: two of one recording each, and one of three recordings in
    turn.

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
            PlayableReconstruction(PLAYABLE_RECONSTRUCTION, takes[:1], PLAYABLE_FRAMES, DEFAULT_NES_FREQUENCY),
            PlayableReconstruction(SECOND_PLAYABLE, takes[1:2], PLAYABLE_FRAMES, DEFAULT_NES_FREQUENCY),
            PlayableReconstruction(STEMS_RECONSTRUCTION, stem_takes, STEM_FRAMES, DEFAULT_NES_FREQUENCY),
            PlayableReconstruction(SHORT_RECONSTRUCTION, stem_takes[:1], STEM_FRAMES, DEFAULT_NES_FREQUENCY),
            StoredReconstruction(OPEN_RECONSTRUCTION),
            stored_recording(),
            StoredProject(SONG, sample=SONG_SAMPLE, instrument=SONG_INSTRUMENT),
        ),
    )
