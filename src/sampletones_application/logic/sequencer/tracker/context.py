from typing import Callable, List, Tuple

from sampletones_application.view_model.sequencer.tracker import (
    SequencerContextRowViewModel,
    SequencerRowViewModel,
)

FrameRows = Callable[[int], Tuple[SequencerRowViewModel, ...]]
ContextRows = Tuple[SequencerContextRowViewModel, ...]


def rows_before(
    frame_index: int,
    reach: int,
    frame_rows: FrameRows,
) -> ContextRows:
    """The last ``reach`` rows the song plays before ``frame_index``, in playing order.

    The walk goes back a frame at a time, so a frame shorter than what is left to reach gives all
    of its rows and the one before it gives the rest. It ends at the song's first frame.

    Args:
        frame_index: The frame the rows lead into.
        reach: How many rows to gather.
        frame_rows: Reads the rows of one frame.

    Returns:
        ContextRows: At most ``reach`` rows, the nearest to the frame last.
    """
    gathered: List[SequencerContextRowViewModel] = []
    frame = frame_index - 1
    while len(gathered) < reach and frame >= 0:
        rows = frame_rows(frame)
        taken = rows[max(0, len(rows) - (reach - len(gathered))) :]
        gathered[:0] = [SequencerContextRowViewModel(frame_index=frame, row=row) for row in taken]
        frame -= 1

    return tuple(gathered)


def rows_after(
    frame_index: int,
    frame_count: int,
    reach: int,
    frame_rows: FrameRows,
) -> ContextRows:
    """The first ``reach`` rows the song plays after ``frame_index``, in playing order.

    The walk goes on a frame at a time, so a frame shorter than what is left to reach gives all of
    its rows and the one after it gives the rest. It ends at the song's last frame.

    Args:
        frame_index: The frame the rows follow.
        frame_count: How many frames the order holds.
        reach: How many rows to gather.
        frame_rows: Reads the rows of one frame.

    Returns:
        ContextRows: At most ``reach`` rows, the nearest to the frame first.
    """
    gathered: List[SequencerContextRowViewModel] = []
    frame = frame_index + 1
    while len(gathered) < reach and frame < frame_count:
        rows = frame_rows(frame)
        taken = rows[: reach - len(gathered)]
        gathered.extend(SequencerContextRowViewModel(frame_index=frame, row=row) for row in taken)
        frame += 1

    return tuple(gathered)
