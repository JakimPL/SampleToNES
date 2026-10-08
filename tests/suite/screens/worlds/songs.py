from pathlib import Path
from typing import Final

from automation.worlds.home import World
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.suite.screens.seeds.projects import (
    ArrangedProject,
    LongEnvelopeProject,
    OverlongProject,
    ReleasingInstrumentFile,
    TwoTuningsProject,
)
from tests.suite.screens.worlds.recordings import playing_world

ARRANGED_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Arranged.stp"
LINE: Final[str] = "Line"
BASS_VOICE: Final[str] = "Bass"
PAD: Final[str] = "Pad"
PAD_ROW: Final[int] = 4
BASS_ROW: Final[int] = 8
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


def sequencer_world() -> World:
    """A home holding :data:`ARRANGED_PROJECT`, its voices placed on its first pattern, and the playing
    world's files.

    The project's sample :data:`LINE` starts the pattern on Pulse 1, its instrument :data:`PAD`
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
