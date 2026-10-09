from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.features import RESTING_REFERENCE_PERIOD, RESTING_REFERENCE_PITCH, speaks_in_periods
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.performance.song import song_instructions
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.pitch import Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.song import Song
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from tests.suite.performance import reconstruction_of

TRANSPOSED_ROWS_PER_PATTERN: Final[int] = 16
CONTOUR_VOLUME: Final[int] = 12
CONTOUR_DUTY: Final[int] = 2
CONTOURS: Final[Dict[ChannelName, Tuple[int, ...]]] = {
    ChannelName.PULSE1: (69, 73, 76, 81),
    ChannelName.TRIANGLE: (69, 76),
    ChannelName.NOISE: (3, 4),
}
CONTOUR_TICKS: Final[Dict[ChannelName, int]] = {
    ChannelName.PULSE1: 3,
    ChannelName.TRIANGLE: 4,
    ChannelName.NOISE: 5,
}
TRANSPOSED_CHANNELS: Final[Tuple[ChannelName, ...]] = tuple(CONTOURS)


def contour_instruction(channel_name: ChannelName, value: int) -> InstructionUnion:
    """One sounding frame of a channel at a pitch, or at a period on noise."""
    match channel_name:
        case ChannelName.NOISE:
            return NoiseInstruction(on=True, period=value, volume=CONTOUR_VOLUME, short=False)
        case ChannelName.TRIANGLE:
            return TriangleInstruction(on=True, pitch=value)
        case _:
            return PulseInstruction(on=True, pitch=value, volume=CONTOUR_VOLUME, duty_cycle=CONTOUR_DUTY)


def contour_sample(channel_name: ChannelName, frames: int) -> Sample:
    """A sample stepping through its channel's contour for ``frames`` frames, a few frames per step.

    A contour that keeps moving is what makes the step a note has reached audible, so a transpose
    row placing its table at the wrong step shows up as a wrong pitch.
    """
    contour = CONTOURS[channel_name]
    hold = CONTOUR_TICKS[channel_name]
    instructions = [contour_instruction(channel_name, contour[(tick // hold) % len(contour)]) for tick in range(frames)]
    return Sample(name=f"Contour ({channel_name})", reconstruction=reconstruction_of(channel_name, instructions))


def settling_sample(channel_name: ChannelName, frames: int) -> Sample:
    """A sample stepping once through its channel's contour, then holding the last step for ``frames`` frames in all.

    Its arpeggio stops changing early while the note goes on sounding, so a tracker whose arpeggio
    halts once it has played its items shows a transpose row landing after that.
    """
    contour = CONTOURS[channel_name]
    hold = CONTOUR_TICKS[channel_name]
    instructions = [
        contour_instruction(channel_name, contour[min(tick // hold, len(contour) - 1)]) for tick in range(frames)
    ]
    return Sample(name=f"Settling ({channel_name})", reconstruction=reconstruction_of(channel_name, instructions))


def flat_sample(channel_name: ChannelName, value: int, frames: int) -> Sample:
    """A sample holding one pitch, or one period on noise, for ``frames`` frames."""
    instructions = [contour_instruction(channel_name, value)] * frames
    return Sample(name=f"Flat ({channel_name})", reconstruction=reconstruction_of(channel_name, instructions))


def flat_instrument(channel_name: ChannelName, value: int) -> Instrument:
    """An instrument resting at one pitch, or one period on noise, holding the contour volume.

    It writes no contour of its own, so every tick sounds the pitch its row started it at, which
    is what a case about an instrument taking the channel's pitch reads back.
    """
    return Instrument(
        name=f"Flat instrument ({channel_name})",
        envelopes=InstrumentEnvelopes(volume=Envelope(items=(CONTOUR_VOLUME,))),
        initial_pitch=RESTING_REFERENCE_PITCH if speaks_in_periods(channel_name) else value,
        initial_period=value if speaks_in_periods(channel_name) else RESTING_REFERENCE_PERIOD,
    )


def rows_with(*cells: Tuple[int, Row]) -> List[Row]:
    """A pattern's rows, blank apart from the ones given by their index."""
    rows = [Row() for _ in range(TRANSPOSED_ROWS_PER_PATTERN)]
    for row_index, row in cells:
        rows[row_index] = row

    return rows


def note(voice: VoiceUnion, transpose: Optional[int] = None) -> Row:
    """A row starting ``voice``, at ``transpose`` where one is given."""
    return Row(command=NoteOn(voice_id=voice.id), pitch=Step(value=transpose) if transpose is not None else None)


def one_channel_project(
    voices: Sequence[VoiceUnion],
    channel_name: ChannelName,
    patterns: Mapping[int, List[Row]],
    order: Sequence[Optional[int]],
    *,
    settings: ProjectSettings,
) -> Project:
    """A project playing ``voices`` on one channel through the patterns ``order`` names."""
    channels = {
        name: Channel(
            name=name,
            patterns={index: Pattern(rows=rows) for index, rows in patterns.items()} if name == channel_name else {},
        )
        for name in ChannelName.items()
    }
    project = Project.create(title="Transposes", author="Tester", settings=settings)
    for voice in voices:
        project.voices.append(voice)

    project.song = Song(
        rows_per_pattern=TRANSPOSED_ROWS_PER_PATTERN,
        order=[{channel_name: index} for index in order],
        channels=channels,
    )
    return project


def sounded_pitches(project: Project, channel_name: ChannelName) -> List[Optional[int]]:
    """What the song's walk sounds on one channel each tick: the pitch, or on noise the period register.

    The noise register counts the periods from the fastest while the project counts them from the
    slowest, so a period reaches the register as its complement. A tick the channel rests on is
    ``None``.
    """
    sounded: List[Optional[int]] = []
    for instruction in song_instructions(project)[channel_name]:
        match instruction:
            case PulseInstruction():
                sounded.append(instruction.pitch if instruction.on and instruction.volume else None)
            case TriangleInstruction():
                sounded.append(instruction.pitch if instruction.on else None)
            case NoiseInstruction():
                sounded.append(MAX_PERIOD - instruction.period if instruction.on and instruction.volume else None)

    return sounded
