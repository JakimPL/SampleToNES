from bisect import bisect_right
from typing import Dict, Final, List, Mapping, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction

from .midi import Note, Track

VOICE_CHANNELS: Final[Dict[str, ChannelName]] = {
    "p1": ChannelName.PULSE1,
    "p2": ChannelName.PULSE2,
    "tr": ChannelName.TRIANGLE,
    "no": ChannelName.NOISE,
}
VOLUME_CONTROLLER: Final[int] = 11
TIMBRE_CONTROLLER: Final[int] = 12
TRIANGLE_OCTAVE: Final[int] = 12
NOISE_PITCHES: Final[int] = 16
SHORT_MODE: Final[int] = 1
FIRST_DUTY_CYCLE: Final[int] = 2
FRAME_CENTER: Final[float] = 0.5

Events = List[Tuple[float, int]]


def nesmdb_frames(
    tracks: Mapping[str, Track],
    *,
    start_frame: int,
    frames: int,
    rate: int,
) -> Dict[ChannelName, List[InstructionUnion]]:
    """The frames an NES-MDB piece plays over a window, read at the middle of each frame.

    NES-MDB writes each channel as a named track. A note's velocity is the volume it starts at,
    controller 11 moves the volume while it sounds, and controller 12 sets the pulse's duty cycle or
    the noise channel's mode. The triangle's note names the pitch it sounds, an octave below the
    note it is played on, and the noise channel's note counts its sixteen periods from the lowest.

    Args:
        tracks: The piece's tracks by name.
        start_frame: The first frame of the window.
        frames: How many frames the window holds.
        rate: The frames per second.

    Returns:
        Dict[ChannelName, List[InstructionUnion]]: One instruction per frame for each channel the piece writes.

    Raises:
        ValidationError: If a note lies outside the range its channel's instruction takes.
    """
    streams: Dict[ChannelName, List[InstructionUnion]] = {}
    for name, track in tracks.items():
        channel = VOICE_CHANNELS.get(name)
        if channel is None:
            continue

        times = [(start_frame + frame + FRAME_CENTER) / rate for frame in range(frames)]
        streams[channel] = [_frame(channel, track, time) for time in times]

    return streams


def _frame(channel: ChannelName, track: Track, time: float) -> InstructionUnion:
    note = _sounding(track.notes, time)
    timbres = track.controllers.get(TIMBRE_CONTROLLER, [])
    match channel:
        case ChannelName.TRIANGLE:
            if note is None:
                return TriangleInstruction.null_instruction()
            return TriangleInstruction(on=True, pitch=note.pitch + TRIANGLE_OCTAVE)
        case ChannelName.NOISE:
            volume = _volume(track, note, time)
            if note is None or not volume:
                return NoiseInstruction.null_instruction()
            short = _latest(timbres, time) == SHORT_MODE
            return NoiseInstruction(on=True, period=NOISE_PITCHES - note.pitch, volume=volume, short=short)
        case _:
            volume = _volume(track, note, time)
            if note is None or not volume:
                return PulseInstruction.null_instruction()
            duty = _latest(timbres, time)
            return PulseInstruction(
                on=True,
                pitch=note.pitch,
                volume=volume,
                duty_cycle=FIRST_DUTY_CYCLE if duty is None else duty,
            )


def _sounding(notes: List[Note], time: float) -> Optional[Note]:
    index = bisect_right([note.start for note in notes], time) - 1
    if index < 0 or notes[index].end <= time:
        return None

    return notes[index]


def _volume(track: Track, note: Optional[Note], time: float) -> int:
    """The volume at ``time``: the note's velocity, then whatever controller 11 last set while it sounds."""
    if note is None:
        return 0

    changes = [
        (moment, value) for moment, value in track.controllers.get(VOLUME_CONTROLLER, []) if moment >= note.start
    ]
    changed = _latest(changes, time)
    return note.velocity if changed is None else changed


def _latest(events: Events, time: float) -> Optional[int]:
    index = bisect_right([moment for moment, _ in events], time) - 1
    return events[index][1] if index >= 0 else None
