from typing import Final

import pytest
from pytest import MarkDecorator

FINAL_ZERO: Final[str] = (
    "rule 3: the device's final zero reaches whichever player registered for positions last, at every start and stop"
)
NO_CAUSE: Final[str] = "rule 3: an end report names no cause"
SILENT_PREVIEW_END: Final[str] = "rule 3: a voice or file preview hears nothing of its end"
SILENT_SONG_STOP: Final[str] = "rule 3: a song its owner or the transport stops sends no end report"
STOP_ANY_BUFFER: Final[str] = "rule 3: a player's stop silences whatever buffer the device plays"
SECOND_STREAM: Final[str] = "rule 2: a takeover from a writer that outlived the stop's wait opens a second stream"
POSITION_AHEAD: Final[str] = "rule 4: a player's position counts the block still being written"
LOST_CLICK: Final[str] = "rule 4: a click while the sound winds down moves a playback that is ending"
DEVICE_RATE: Final[str] = "rule 5: a buffer plays at the device's rate"
STOP_WAITS: Final[str] = "rule 6: Stop joins the audio threads on the render thread"
TAIL_ON_STOP: Final[str] = "rule 6: a stop or a takeover plays the tail out"
PAUSED_FAILURE: Final[str] = "rule 7: a song failing while paused and then stopped never tells the failure"
UNREAD_FILE: Final[str] = "rule 7: a file preview that fails to read its file raises past its listener"


def broken(*reasons: str) -> MarkDecorator:
    """The strict expected failure of a case today's playback fails, naming each contract rule it breaks.

    Each reason has an entry in the ledger. The rework closing a break removes the mark from every case
    naming it, so a case that starts passing while its mark stands fails the run.
    """
    return pytest.mark.xfail(strict=True, reason="; ".join(reasons))
