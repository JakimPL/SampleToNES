from dataclasses import dataclass
from typing import AbstractSet, Final, FrozenSet, List, Sequence

from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.instructions import InstructionUnion

UNHELD_STEM_IDS: Final[FrozenSet[int]] = frozenset({RESTING_STEM_ID, AUTHORED_STEM_ID})


@dataclass(frozen=True)
class CarriedEdit:
    """One channel as an edit leaves it: what each frame plays, and who plays it.

    Attributes:
        instructions: The channel's stream, one instruction per frame.
        stem_ids: The stem holding each of those frames.
    """

    instructions: List[InstructionUnion]
    stem_ids: List[int]


def writes_reach(stem_ids: Sequence[int], heard: AbstractSet[int]) -> List[bool]:
    """Whether an edit reaches each frame of a channel.

    A frame accepts a gesture where the recording holding it is among the ones the reader
    hears, where it rests, and where the reader wrote it, so narrowing what is heard narrows
    what is changed with it.

    Args:
        stem_ids: The stem holding each frame of the channel.
        heard: The recordings the reader hears on that channel.

    Returns:
        List[bool]: One flag per frame, true where an edit writes it.
    """
    return [stem_id in heard or stem_id in UNHELD_STEM_IDS for stem_id in stem_ids]


def carried_edit(
    previous: Sequence[InstructionUnion],
    stem_ids: Sequence[int],
    proposed: Sequence[InstructionUnion],
    *,
    heard: AbstractSet[int],
) -> CarriedEdit:
    """The channel an edit leaves, with every frame's owner carried through it.

    An edit rewrites what a frame plays and leaves who plays it, so a frame sounding before and
    after keeps its owner, one the edit quiets rests, and one it brings into play is the
    reader's own. A frame written past the end of the stream answers the same way. Frames
    outside the reader's scope stand as they are, in what they play and in how far the stream
    runs, which is what lets one recording's part be shaped while the recordings beside it
    carry on.

    Args:
        previous: The stream the channel played.
        stem_ids: The stem holding each of those frames.
        proposed: The stream the edit offers.
        heard: The recordings the reader hears on this channel.

    Returns:
        CarriedEdit: The stream the channel now plays, and the stem holding each of its frames.
    """
    reach = writes_reach(stem_ids, heard)
    instructions = _written_stream(previous, proposed, reach)
    carried: List[int] = []
    for frame, instruction in enumerate(instructions):
        stood = frame < len(previous)
        owner = stem_ids[frame] if frame < len(stem_ids) else RESTING_STEM_ID
        carried.append(_owner_of(instruction, owner if stood else RESTING_STEM_ID))

    return CarriedEdit(instructions=instructions, stem_ids=carried)


def _written_stream(
    previous: Sequence[InstructionUnion],
    proposed: Sequence[InstructionUnion],
    reach: Sequence[bool],
) -> List[InstructionUnion]:
    """What every frame of the channel plays once the edit has been carried into it.

    The edit states each frame it reaches and the channel states the rest, so a frame held by a
    recording the reader left out keeps what it played whether the edit rewrote it or dropped
    it from the end.
    """
    written = [instruction if _reaches(reach, frame) else previous[frame] for frame, instruction in enumerate(proposed)]
    held = _held_beyond(previous, len(proposed), reach)
    if held > len(proposed):
        null: InstructionUnion = type(previous[0]).null_instruction()
        written.extend(null if _reaches(reach, frame) else previous[frame] for frame in range(len(proposed), held))

    return written


def _reaches(reach: Sequence[bool], frame: int) -> bool:
    """Whether an edit writes one frame, which it does wherever the stream ran no further."""
    return frame >= len(reach) or reach[frame]


def _held_beyond(
    previous: Sequence[InstructionUnion],
    proposed_length: int,
    reach: Sequence[bool],
) -> int:
    """How far a channel runs once an edit has shortened it.

    An edit drops the frames it reaches, so the stream runs through the last frame standing
    outside its scope and the frames it did reach rest along the way. A scope covering every
    frame past the edit leaves the channel exactly as long as the edit states.
    """
    for frame in reversed(range(proposed_length, len(previous))):
        if not _reaches(reach, frame):
            return frame + 1

    return proposed_length


def _owner_of(instruction: InstructionUnion, owner: int) -> int:
    """The stem a frame holds once the edit has settled what it plays.

    Rest and silence name the same frames, so a silent frame rests whoever held it, a sounding
    frame keeps the owner it already had, and one coming into play is the reader's own.
    """
    if not instruction.on:
        return RESTING_STEM_ID

    if owner == RESTING_STEM_ID:
        return AUTHORED_STEM_ID

    return owner
