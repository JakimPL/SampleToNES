import math
from dataclasses import dataclass
from typing import Final, Iterable, List, Mapping, Optional, Sequence

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TonalInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import PitchLine, Truth, sounding_pitches

from .frames import Frame, common_length, sounds
from .protocol import Judgment
from .transcription import timbre_of

STABILITY_REFEREE: Final[str] = "stability"
TOGGLES: Final[str] = "toggles"
MOVES: Final[str] = "moves"
PITCH_MOTION: Final[str] = "pitch-motion"
LEVEL_MOTION: Final[str] = "level-motion"
DUTY_SWITCHES: Final[str] = "duty-switches"
DECIBELS_PER_AMPLITUDE_DECADE: Final[float] = 20.0
REFERENCE_FREQUENCY: Final[float] = 440.0
SEMITONES_PER_OCTAVE: Final[int] = 12


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
    sound changes where its pitch lines start, stop or move to another note.

    The score is the changes per second the conversion makes beyond the sound's own, toggles and moves
    together, and the readings behind it are each of the two. Three more readings say by how much
    the sounding channels move, beyond the sound's own motion, per second:

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
        length = common_length(*_written_streams(truth), *played_streams.values())
        if not length:
            return None

        seconds = length / reconstruction.config.library.nes_frequency

        played = stream_changes(played_streams, length)
        written = (
            stream_changes(truth.instructions, length) if truth.instructions else line_changes(truth.pitches, length)
        )
        toggles = max(played.toggles - written.toggles, 0) / seconds
        moves = max(played.moves - written.moves, 0) / seconds
        components = {TOGGLES: toggles, MOVES: moves}
        played_lines = sounding_pitches(played_streams, reconstruction.config)
        components[PITCH_MOTION] = _excess(
            pitch_motion(played_lines.values(), length), pitch_motion(truth.pitches.values(), length), seconds
        )
        if truth.instructions:
            components[LEVEL_MOTION] = _excess(
                level_motion(played_streams, length), level_motion(truth.instructions, length), seconds
            )
            components[DUTY_SWITCHES] = _excess(
                duty_switches(played_streams, length), duty_switches(truth.instructions, length), seconds
            )

        return Judgment(score=toggles + moves, components=components)


def stream_changes(instructions: Mapping[ChannelName, Sequence[InstructionUnion]], length: int) -> Changes:
    """The changes every channel's first ``length`` frames make."""
    toggles = moves = 0
    for stream in instructions.values():
        frames: Sequence[Frame] = stream[:length]
        for previous, current in zip(frames, frames[1:]):
            toggles += sounds(previous) != sounds(current)
            moves += sounds(previous) and sounds(current) and _placed(previous) != _placed(current)

    return Changes(toggles=toggles, moves=moves)


def pitch_motion(lines: Iterable[PitchLine], length: int) -> float:
    """The semitones every line travels between consecutive frames it sounds in, summed."""
    travelled = 0.0
    for line in lines:
        frames = line[:length]
        for previous, current in zip(frames, frames[1:]):
            if previous is not None and current is not None:
                travelled += abs(SEMITONES_PER_OCTAVE * math.log2(current / previous))

    return travelled


def level_motion(instructions: Mapping[ChannelName, Sequence[InstructionUnion]], length: int) -> float:
    """The decibels every sounding pulse and noise channel's volume travels between consecutive frames, summed."""
    travelled = 0.0
    for stream in instructions.values():
        frames = stream[:length]
        for previous, current in zip(frames, frames[1:]):
            match previous, current:
                case (PulseInstruction() | NoiseInstruction(), PulseInstruction() | NoiseInstruction()) if (
                    previous.on and current.on and previous.volume and current.volume
                ):
                    travelled += abs(DECIBELS_PER_AMPLITUDE_DECADE * math.log10(current.volume / previous.volume))
                case _:
                    pass

    return travelled


def duty_switches(instructions: Mapping[ChannelName, Sequence[InstructionUnion]], length: int) -> int:
    """How many times a sounding pulse changes timbre between consecutive frames, 25% and 75% being one."""
    switches = 0
    for stream in instructions.values():
        frames = stream[:length]
        for previous, current in zip(frames, frames[1:]):
            match previous, current:
                case (PulseInstruction(), PulseInstruction()) if previous.on and current.on:
                    switches += timbre_of(previous.duty_cycle) != timbre_of(current.duty_cycle)
                case _:
                    pass

    return switches


def _excess(played: float, written: float, seconds: float) -> float:
    return max(played - written, 0.0) / seconds


def line_changes(pitches: Mapping[str, PitchLine], length: int) -> Changes:
    """The changes every pitch line's first ``length`` frames make, a move being a step to another note."""
    toggles = moves = 0
    for line in pitches.values():
        notes = [_note(frequency) for frequency in line[:length]]
        for previous, current in zip(notes, notes[1:]):
            toggles += (previous is None) != (current is None)
            moves += previous is not None and current is not None and previous != current

    return Changes(toggles=toggles, moves=moves)


def _written_streams(truth: Truth) -> List[Sequence[object]]:
    """The streams a sound's own changes are read from: its frames where written, else its pitch lines."""
    if truth.instructions:
        return list(truth.instructions.values())

    return list(truth.pitches.values())


def _placed(frame: Frame) -> Optional[int]:
    match frame:
        case TonalInstruction():
            return frame.pitch
        case NoiseInstruction():
            return frame.period
        case _:
            return None


def _note(frequency: Optional[float]) -> Optional[int]:
    if frequency is None:
        return None

    return round(SEMITONES_PER_OCTAVE * math.log2(frequency / REFERENCE_FREQUENCY))
