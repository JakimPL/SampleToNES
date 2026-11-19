from typing import Tuple

from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.formats.famitracker.model.pattern import NoteCell
from sampletones_core.formats.famitracker.specification.parameters import (
    ENGINE_SPEED_MACHINE_DEFAULT,
    Machine,
)
from sampletones_core.formats.famitracker.specification.patterns import (
    NOTE_RANGE,
    PITCH_OCTAVE_OFFSET,
)
from sampletones_core.utils.frequencies import played_pitch
from sampletones_shared.constants.nes import NTSC_FREQUENCY, PAL_FREQUENCY


def pitch_to_note_cell(pitch: int) -> NoteCell:
    """Converts an absolute pitch to a FamiTracker note cell.

    The pitch is held to the notes a channel plays, C-0..B-7, which are the notes a cell names, so
    an extreme transposition lands on the nearest playable note.
    """
    played = played_pitch(pitch)
    note = played % NOTE_RANGE + 1
    octave = played // NOTE_RANGE - PITCH_OCTAVE_OFFSET
    return NoteCell(note=note, octave=octave)


def period_to_note_cell(period: int) -> NoteCell:
    """Converts a noise period index to a FamiTracker note cell.

    The period wraps into the 16 noise periods, matching how FamiTracker reduces a
    noise note to its low four bits.
    """
    value = period % NUM_PERIODS
    note = value % NOTE_RANGE + 1
    octave = value // NOTE_RANGE
    return NoteCell(note=note, octave=octave)


def resolve_machine(nes_frequency: int) -> Tuple[Machine, int]:
    """Maps the project's NES refresh rate to a machine and engine-speed override.

    Standard rates select their machine and leave the engine at its default refresh;
    any other rate keeps NTSC and carries the rate as an explicit engine speed.
    """
    if nes_frequency == NTSC_FREQUENCY:
        return Machine.NTSC, ENGINE_SPEED_MACHINE_DEFAULT

    if nes_frequency == PAL_FREQUENCY:
        return Machine.PAL, ENGINE_SPEED_MACHINE_DEFAULT

    return Machine.NTSC, nes_frequency
