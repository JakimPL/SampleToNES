from pathlib import Path
from typing import Dict, Final, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.tracker import BlockNote, SequencerTrackerLogic, TrackerBlock
from sampletones_application.logic.sequencer.tracker.block import BlockKey
from sampletones_application.view_model.sequencer.slot import SUBCOLUMNS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import NoteCommand
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.utils.display import (
    BLANK,
    NOTE_BLANK,
    NOTE_OFF,
    display_id,
)
from sampletones_shared.constants.symbols import MINUS, MIXED, PLUS

SAMPLE_LENGTH: Final[int] = 64
COLUMN_SEPARATOR: Final[str] = "|"
UNKNOWN_SAMPLE: Final[str] = "!!"
UNKNOWN_SAMPLE_ID: Final[str] = "a-sample-no-project-holds"


def sample_reconstruction(generators: Sequence[GeneratorName]) -> Reconstruction:
    """A reconstruction carrying one instruction on each of ``generators``.

    The channels a reconstruction covers are what a sample governs in the sequencer, so this is
    the knob a sequencer test turns: the audio itself is silent, since what is under test is which
    channels a sample reaches and not how it sounds.
    """
    instructions = {
        generator: [
            PulseInstruction(
                on=True,
                pitch=60,
                volume=8,
                duty_cycle=0,
            )
        ]
        for generator in generators
    }
    approximations = {generator: np.zeros(SAMPLE_LENGTH, dtype=np.float32) for generator in generators}
    return Reconstruction.create(
        approximation=np.zeros(SAMPLE_LENGTH, dtype=np.float32),
        approximations=approximations,
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


def render_frame(tracker_logic: SequencerTrackerLogic) -> Tuple[str, ...]:
    """Every row of the frame shown, each read as the four channel cells the grid draws.

    A row is written the way it appears on screen, so an expectation and a screenshot read alike.
    The sample column is left out because it holds nothing of its own: it summarises these four,
    and stating it again would pin the summary rather than what a gesture wrote.
    """
    grid = tracker_logic.build_grid()
    return tuple(
        f" {COLUMN_SEPARATOR} ".join(row.cells[generator].label for generator in GeneratorName.items())
        for row in grid.rows
    )


def render_slots(
    controller: ProjectController,
    frame_index: int,
) -> str:
    """The pattern each channel plays at a frame, which is what tells a blank pattern from none.

    A frame renders the same either way, so this is the reading that shows a write materialising a
    pattern the channel had not held before.
    """
    frame = controller.project.song.order[frame_index]
    return " ".join(display_id(frame.get(generator)) for generator in GeneratorName.items())


def parse_block(
    rows: Sequence[str],
    *,
    first_subcolumn: SubColumn,
    sample_ids: Sequence[str],
) -> TrackerBlock:
    """Reads a block written the way the grid draws it, one line per row.

    Tokens run from ``first_subcolumn`` and cycle through the subcolumns in order, so a line
    carries ``|`` at each column boundary it crosses and the bars are held against the subcolumn
    the block begins on. A ``?`` states that the block says nothing about that cell, which is what
    leaves it out of the maps entirely.

    A note names its sample by the position the grid prints, resolved through ``sample_ids``;
    ``!!`` names a sample no project holds.

    Raises:
        ValueError: if the rows differ in width, or a bar falls where no column boundary does.
    """
    first_slot = SUBCOLUMNS.index(first_subcolumn)
    notes: Dict[BlockKey, Optional[BlockNote]] = {}
    transposes: Dict[BlockKey, Optional[int]] = {}
    volumes: Dict[BlockKey, Optional[int]] = {}
    lines = [_tokens(line, first_slot) for line in rows]
    widths = {len(tokens) for tokens in lines}
    if len(widths) != 1:
        raise ValueError(f"A block's rows differ in width: {sorted(widths)}")

    for row_offset, tokens in enumerate(lines):
        for offset, token in enumerate(tokens):
            slot_offset = first_slot + offset
            key = (row_offset, slot_offset)
            if token == MIXED:
                continue

            match SUBCOLUMNS[slot_offset % len(SUBCOLUMNS)]:
                case SubColumn.INSTRUMENT:
                    notes[key] = parse_note(token, sample_ids)
                case SubColumn.TRANSPOSE:
                    transposes[key] = parse_transpose(token)
                case SubColumn.VOLUME:
                    volumes[key] = parse_volume(token)

    return TrackerBlock(
        row_count=len(rows),
        first_slot=first_slot,
        last_slot=first_slot + widths.pop() - 1,
        notes=notes,
        transposes=transposes,
        volumes=volumes,
    )


def fill_frame(
    tracker_logic: SequencerTrackerLogic,
    rows: Sequence[str],
    *,
    sample_ids: Sequence[str],
) -> None:
    """Writes a frame stated the way the grid draws it, one channel cell at a time.

    Each cell reaches its own channel, so a setup states the frame it wants while the sample
    column's fan-out stays out of it — which leaves the gesture under test the only thing that
    exercised it.
    """
    for row_index, line in enumerate(rows):
        for generator, cell in zip(GeneratorName.items(), line.split(COLUMN_SEPARATOR)):
            _fill_cell(
                tracker_logic,
                row_index,
                generator,
                cell.split(),
                sample_ids,
            )


def parse_note(
    token: str,
    sample_ids: Sequence[str],
) -> Optional[BlockNote]:
    """The note a token names: a sample by the position it prints, a cut, or emptiness."""
    if token == display_id(None):
        return None

    if token == NOTE_OFF:
        return NoteOff()

    if token == UNKNOWN_SAMPLE:
        return UNKNOWN_SAMPLE_ID

    return sample_ids[int(token, 16)]


def parse_transpose(token: str) -> Optional[int]:
    if token == NOTE_BLANK:
        return None

    magnitude = int(token[1:], 16)
    return -magnitude if token.startswith(MINUS) else magnitude


def parse_volume(token: str) -> Optional[int]:
    if token == BLANK:
        return None

    return int(token, 16)


def _fill_cell(
    tracker_logic: SequencerTrackerLogic,
    row_index: int,
    generator: GeneratorName,
    tokens: Sequence[str],
    sample_ids: Sequence[str],
) -> None:
    """Writes the values one channel cell states, passing over a cell that states none.

    A cell is written whole where it carries anything, so the row it lands on materialises exactly
    once however many of its subcolumns hold a value.
    """
    note = parse_note(tokens[0], sample_ids)
    transpose = parse_transpose(tokens[1])
    volume = parse_volume(tokens[2])
    if note is None and transpose is None and volume is None:
        return

    tracker_logic.set_row(
        generator,
        row_index,
        command=_command(note, generator),
        transpose=transpose,
        volume=volume,
    )


def _command(
    note: Optional[BlockNote],
    generator: GeneratorName,
) -> Optional[NoteCommand]:
    """The command a note becomes in the channel it is written to, which is what carries its pitch."""
    match note:
        case NoteOff():
            return note
        case str() as sample_id:
            return Instrument(sample_id=sample_id, generator_name=generator)
        case None:
            return None


def _tokens(line: str, first_slot: int) -> List[str]:
    """The values a line states, checked against the columns a block starting at ``first_slot`` spans.

    Raises:
        ValueError: if a bar falls where no column boundary does.
    """
    groups = [group.split() for group in line.split(COLUMN_SEPARATOR)]
    tokens = [token for group in groups for token in group]
    widths = [len(group) for group in groups]
    expected = _column_widths(first_slot, len(tokens))
    if widths != expected:
        raise ValueError(f"A block line's columns hold {widths} values where its origin spans {expected}: {line!r}")

    return tokens


def _column_widths(first_slot: int, count: int) -> List[int]:
    """How many values each column a block spans contributes, the first starting part way in."""
    widths: List[int] = []
    width = len(SUBCOLUMNS) - first_slot
    remaining = count
    while remaining > 0:
        widths.append(min(width, remaining))
        remaining -= widths[-1]
        width = len(SUBCOLUMNS)

    return widths
