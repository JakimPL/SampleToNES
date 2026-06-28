"""Playhead index remapping for structural edits to the order during playback.

The synthesiser tracks the live playhead as an index into ``Song.order``. Inserting,
removing, or moving a frame shifts those indices, so after such an edit the playhead
must be remapped to keep pointing at the frame that was actually sounding. These are
pure index functions, so the rules can be unit-tested in isolation.
"""


def remap_after_insert(playhead: int, inserted_index: int) -> int:
    """A frame inserted at or before the playhead pushes it one position later."""
    return playhead + 1 if inserted_index <= playhead else playhead


def remap_after_remove(playhead: int, removed_index: int, new_length: int) -> int:
    """A frame removed before the playhead pulls it one position earlier.

    Removing the playing frame itself keeps the index (it now addresses the frame that
    followed), clamped to the last remaining frame; an emptied order pins the playhead at 0.
    """
    if removed_index < playhead:
        return playhead - 1

    if removed_index == playhead:
        return min(playhead, new_length - 1) if new_length > 0 else 0

    return playhead


def remap_after_move(playhead: int, from_index: int, to_index: int) -> int:
    """The playing frame follows itself when moved; otherwise it shifts by the gap the
    move opens and closes (equivalent to a removal at ``from`` then an insertion at ``to``)."""
    if playhead == from_index:
        return to_index

    shifted = playhead - 1 if from_index < playhead else playhead
    return shifted + 1 if to_index <= shifted else shifted
