from bisect import bisect_right
from typing import Dict, Final, List, Mapping, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction

from .midi import Note, Track
from .truth import frame_middles

VOICE_CHANNELS: Final[Dict[str, ChannelName]] = {
    "p1": ChannelName.PULSE1,
    "p2": ChannelName.PULSE2,
    "tr": ChannelName.TRIANGLE,
    "no": ChannelName.NOISE,
}
VOLUME_CONTROLLER: Final[int] = 11
TIMBRE_CONTROLLER: Final[int] = 12
TRIANGLE_OCTAVE: Final[int] = 12
SHORT_MODE: Final[int] = 1
INITIAL_DUTY_CYCLE: Final[int] = 2

Events = List[Tuple[float, int]]


def nesmdb_frames(
    tracks: Mapping[str, Track],
    *,
    start_frame: int,
    frames: int,
    rate: int,
) -> Dict[ChannelName, List[InstructionUnion]]:
    """The frames an NES-MDB piece plays over a window, each read at its middle.

    NES-MDB writes each channel as a named track, and a track of another name is left out. A note's
    velocity is the volume it starts at, controller 11 moves the volume while it sounds, and
    controller 12 sets the pulse's duty cycle or the noise channel's mode. The triangle's note names
    the pitch it sounds, an octave below the note it is played on, and the noise channel's note counts
    its sixteen periods from the lowest.

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
    times: List[float] = frame_middles(start_frame, frames, rate).tolist()
    streams: Dict[ChannelName, List[InstructionUnion]] = {}
    for name, track in tracks.items():
        channel = VOICE_CHANNELS.get(name)
        if channel is not None:
            streams[channel] = [_frame(channel, track, time) for time in times]

    return streams


def _frame(channel: ChannelName, track: Track, time: float) -> InstructionUnion:
    """What ``channel`` plays at ``time``: the note sounding then, at the volume and timbre the track holds."""
    note = _sounding(track.notes, time)
    match channel:
        case ChannelName.TRIANGLE:
            return _triangle_frame(note)
        case ChannelName.NOISE:
            return _noise_frame(note, _volume(track, note, time), _timbre(track, time))
        case _:
            return _pulse_frame(note, _volume(track, note, time), _timbre(track, time))


def _triangle_frame(note: Optional[Note]) -> TriangleInstruction:
    """The triangle sounding ``note``, played an octave above it at the one level the triangle has."""
    if note is None:
        return TriangleInstruction.null_instruction()

    return TriangleInstruction(on=True, pitch=note.pitch + TRIANGLE_OCTAVE)


def _noise_frame(note: Optional[Note], volume: int, timbre: Optional[int]) -> NoiseInstruction:
    """The noise sounding ``note`` at ``volume``, short where the timbre sets the short mode; silent at volume 0."""
    if note is None or not volume:
        return NoiseInstruction.null_instruction()

    return NoiseInstruction(on=True, period=NUM_PERIODS - note.pitch, volume=volume, short=timbre == SHORT_MODE)


def _pulse_frame(note: Optional[Note], volume: int, timbre: Optional[int]) -> PulseInstruction:
    """A pulse sounding ``note`` at ``volume`` with the duty cycle the timbre sets; silent at volume 0.

    Before the piece sets a duty cycle, a pulse plays at ``INITIAL_DUTY_CYCLE``.
    """
    if note is None or not volume:
        return PulseInstruction.null_instruction()

    duty_cycle = INITIAL_DUTY_CYCLE if timbre is None else timbre
    return PulseInstruction(on=True, pitch=note.pitch, volume=volume, duty_cycle=duty_cycle)


def _sounding(notes: List[Note], time: float) -> Optional[Note]:
    """The note sounding at ``time``: of the notes started by then and ending after it, the last to start.

    ``notes`` are ordered by their start. Where notes overlap, the latest to start sounds, and the one
    it covers sounds again once it ends. Returns ``None`` where no note sounds at ``time``.
    """
    started = bisect_right([note.start for note in notes], time)
    return next((note for note in reversed(notes[:started]) if note.end > time), None)


def _volume(track: Track, note: Optional[Note], time: float) -> int:
    """The volume at ``time``: the note's velocity, then whatever controller 11 last set since it started."""
    if note is None:
        return 0

    changes = [
        (moment, value) for moment, value in track.controllers.get(VOLUME_CONTROLLER, []) if moment >= note.start
    ]
    changed = _latest(changes, time)
    return note.velocity if changed is None else changed


def _timbre(track: Track, time: float) -> Optional[int]:
    """The value controller 12 last set by ``time``, ``None`` before the piece sets one."""
    return _latest(track.controllers.get(TIMBRE_CONTROLLER, []), time)


def _latest(events: Events, time: float) -> Optional[int]:
    """The value of the last of ``events`` at or before ``time``, ``None`` before the first."""
    index = bisect_right([moment for moment, _ in events], time) - 1
    return events[index][1] if index >= 0 else None
