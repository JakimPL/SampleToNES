import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Dict, Final, Iterable, Iterator, List, Mapping, Optional, Sequence, Sized, Tuple, TypeVar

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TonalInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import PitchLine, Truth, sounding_pitches

from .frames import Frame, common_length, sounds
from .intervals import line_semitones, semitones_between
from .notes import timbre_of
from .protocol import Judgment

STABILITY_REFEREE: Final[str] = "stability"
TOGGLES: Final[str] = "toggles"
MOVES: Final[str] = "moves"
PITCH_MOTION: Final[str] = "pitch-motion"
LEVEL_MOTION: Final[str] = "level-motion"
DUTY_SWITCHES: Final[str] = "duty-switches"
DECIBELS_PER_AMPLITUDE_DECADE: Final[float] = 20.0

Step = TypeVar("Step")
Streams = Mapping[ChannelName, Sequence[InstructionUnion]]


@dataclass(frozen=True)
class Changes:
    """How often channels change across some frames.

    Attributes:
        toggles: How many times a channel turns on or off.
        moves: How many times a sounding channel moves to another note or noise period.
    """

    toggles: int
    moves: int


class StabilityReferee:
    """Reads how much more often a conversion's channels change than the sound it converts does.

    A channel changes where it turns on or off (a toggle), or where it keeps sounding on another note
    or noise period (a move). A sound written as NES frames changes where its frames do. A synthesized
    sound changes where its pitch lines start, stop or move to another note. Every reading counts only
    what the conversion makes beyond the sound's own, per second, so a conversion that changes where its
    sound does reads zero, and one that changes less reads zero too.

    The score is the toggles and moves per second beyond the sound's own, lower being steadier. Each
    of the two is a reading of its own. Three more readings say how far the sounding channels move
    beyond the sound's own motion, per second:

    - ``pitch-motion``: semitones the sounding pitch travels, bends included, so a vibrato the
      conversion follows counts as the sound's own;
    - ``level-motion``: decibels the volume of a sounding pulse or noise channel travels, for a sound
      written as frames;
    - ``duty-switches``: changes of a sounding pulse's timbre, 25% and 75% being one, for a sound
      written as frames.
    """

    @property
    def name(self) -> str:
        return STABILITY_REFEREE

    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]:
        """The changes per second ``reconstruction`` makes beyond those ``truth`` makes.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` where the sound and its conversion share no frame.
        """
        played_streams = reconstruction.instructions
        length = common_length(*_own_streams(truth), *played_streams.values())
        if not length:
            return None

        seconds = length / reconstruction.config.library.nes_frequency

        played = stream_changes(played_streams, length)
        written = _own_changes(truth, length)
        toggles = _excess(played.toggles, written.toggles, seconds)
        moves = _excess(played.moves, written.moves, seconds)
        components = {TOGGLES: toggles, MOVES: moves}
        played_lines = sounding_pitches(played_streams, reconstruction.config)
        components[PITCH_MOTION] = _excess(
            pitch_motion(played_lines.values(), length), pitch_motion(truth.pitches.values(), length), seconds
        )
        if truth.instructions:
            components.update(_frame_motion(played_streams, truth.instructions, length, seconds))

        return Judgment(score=toggles + moves, components=components)


def stream_changes(instructions: Streams, length: int) -> Changes:
    """The changes every channel's first ``length`` frames make."""
    toggles = moves = 0
    for previous, current in _successive(instructions.values(), length):
        toggles += sounds(previous) != sounds(current)
        moves += sounds(previous) and sounds(current) and _placed(previous) != _placed(current)

    return Changes(toggles=toggles, moves=moves)


def line_changes(pitches: Mapping[str, PitchLine], length: int) -> Changes:
    """The changes every pitch line's first ``length`` frames make, a move being a step to another note."""
    toggles = moves = 0
    lines = [line_semitones(line[:length]) for line in pitches.values()]
    for previous, current in _successive(lines, length):
        toggles += (previous is None) != (current is None)
        moves += previous is not None and current is not None and previous != current

    return Changes(toggles=toggles, moves=moves)


def pitch_motion(lines: Iterable[PitchLine], length: int) -> float:
    """The semitones every line travels between consecutive frames it sounds in, summed."""
    travelled = 0.0
    for previous, current in _successive(lines, length):
        if previous is not None and current is not None:
            travelled += abs(semitones_between(current, previous))

    return travelled


def level_motion(instructions: Streams, length: int) -> float:
    """The decibels every sounding pulse and noise channel's volume travels between consecutive frames, summed.

    A volume step is a linear amplitude, so a change between two volumes is twenty times the decade
    logarithm of their ratio. A frame at volume zero holds no level to move from or to, so a step to
    or from it travels nothing.
    """
    travelled = 0.0
    for previous, current in _successive(instructions.values(), length):
        step = _level_step(previous, current)
        if step is not None:
            travelled += step

    return travelled


def duty_switches(instructions: Streams, length: int) -> int:
    """How many times a sounding pulse changes timbre between consecutive frames, 25% and 75% being one."""
    switches = 0
    for previous, current in _successive(instructions.values(), length):
        switches += _switches_timbre(previous, current)

    return switches


def _own_streams(truth: Truth) -> List[Sized]:
    """The streams a sound's own changes are read from: its frames where written, else its pitch lines."""
    if truth.instructions:
        return list(truth.instructions.values())

    return list(truth.pitches.values())


def _own_changes(truth: Truth, length: int) -> Changes:
    """The changes the sound itself makes: its frames' where written, else its pitch lines'."""
    if truth.instructions:
        return stream_changes(truth.instructions, length)

    return line_changes(truth.pitches, length)


def _frame_motion(played: Streams, written: Streams, length: int, seconds: float) -> Dict[str, float]:
    """The level and duty motion per second the conversion's frames make beyond the written frames'."""
    return {
        LEVEL_MOTION: _excess(level_motion(played, length), level_motion(written, length), seconds),
        DUTY_SWITCHES: _excess(duty_switches(played, length), duty_switches(written, length), seconds),
    }


def _excess(played: float, written: float, seconds: float) -> float:
    """How much more the conversion makes than the sound, per second, zero where it makes no more."""
    return max(played - written, 0.0) / seconds


def _successive(streams: Iterable[Sequence[Step]], length: int) -> Iterator[Tuple[Step, Step]]:
    """Every two consecutive frames among each stream's first ``length`` frames, stream by stream."""
    for stream in streams:
        yield from pairwise(stream[:length])


def _placed(frame: Frame) -> Optional[int]:
    """Where a sounding frame places its channel: the note a tonal channel names, the noise's period."""
    match frame:
        case TonalInstruction():
            return frame.pitch
        case NoiseInstruction():
            return frame.period
        case _:
            return None


def _level_step(previous: InstructionUnion, current: InstructionUnion) -> Optional[float]:
    """The decibels a sounding pulse or noise volume moves between two frames, ``None`` where it holds no level."""
    match previous, current:
        case (PulseInstruction() | NoiseInstruction(), PulseInstruction() | NoiseInstruction()) if (
            previous.on and current.on and previous.volume and current.volume
        ):
            return abs(DECIBELS_PER_AMPLITUDE_DECADE * math.log10(current.volume / previous.volume))
        case _:
            return None


def _switches_timbre(previous: InstructionUnion, current: InstructionUnion) -> bool:
    """Whether a pulse sounding in both frames changes timbre between them."""
    match previous, current:
        case (PulseInstruction(), PulseInstruction()) if previous.on and current.on:
            return timbre_of(previous.duty_cycle) != timbre_of(current.duty_cycle)
        case _:
            return False
