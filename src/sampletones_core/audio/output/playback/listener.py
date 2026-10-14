from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol

from sampletones_core.audio.output.ending import Ending
from sampletones_core.audio.output.source import ReportT
from sampletones_shared.types.callback import VoidCallback

if TYPE_CHECKING:
    from .handle import Playback

Post = Callable[[VoidCallback], None]


class PlaybackListener(Protocol[ReportT]):
    """What a playback's owner hears of it, on the thread the output's reports cross to.

    The owner hands itself over as it starts a playback, and every call names the playback it reports on,
    so an owner holding a newer playback tells a late report of an older one apart. Positions arrive in
    the order the device took them, each before the one end report.
    """

    def positioned(self, playback: Playback[ReportT], report: ReportT, /) -> None:
        """Hears where the playback stands, once the device has taken the audio that put it there."""

    def ended(self, playback: Playback[ReportT], ending: Ending, /) -> None:
        """Hears the playback's one end report, which names why it ended."""
