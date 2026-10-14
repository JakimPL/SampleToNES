from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sampletones_core.audio.output import AudioSource, AudioThreads, Ending, GainReader, Playback, PlaybackListener
from sampletones_core.audio.output.playback import PlaybackFeed
from sampletones_core.audio.output.source import ReportT
from sampletones_shared.types.callback import VoidCallback


def _now(delivery: VoidCallback) -> None:
    delivery()


@dataclass
class Claim:
    """One sound an owner asked the stand-in for, and where it stands.

    Attributes:
        source: What the sound reads from.
        rank: The rank it claimed the output at.
        listener: The owner that hears of it.
        engaged: Whether it holds the output.
        paused: Whether its owner holds it paused.
        stopped: Whether its owner stopped it.
    """

    source: AudioSource[Any]
    rank: int
    listener: PlaybackListener[Any]
    engaged: bool = True
    paused: bool = False
    stopped: bool = False


class FakeAudioOutput:
    """The audio output as an owner meets it, with the device's side played by the case.

    Every claim holds the output unless the case declines or refuses claims, and a command reaches the
    source at once while its sound holds the output. The case reports positions and ends to the owner
    through ``report`` and ``end``, on its own thread, the way the render thread hands them over.
    """

    def __init__(self) -> None:
        self.threads = AudioThreads()
        self.playbacks: List[Playback[Any]] = []
        self.declining: bool = False
        self.refusal: Optional[Exception] = None
        self._claims: Dict[PlaybackFeed, Claim] = {}

    def play(
        self,
        source: AudioSource[ReportT],
        *,
        rank: int,
        listener: PlaybackListener[ReportT],
        gain: GainReader,
    ) -> Optional[Playback[ReportT]]:
        if self.refusal is not None:
            raise self.refusal

        if self.declining:
            return None

        playback = Playback(source, gain=gain, listener=listener, post=_now, control=self)
        self._claims[playback] = Claim(source=source, rank=rank, listener=listener)
        self.playbacks.append(playback)
        return playback

    def claim(self, playback: Playback[Any]) -> Claim:
        return self._claims[playback]

    @property
    def latest(self) -> Playback[Any]:
        return self.playbacks[-1]

    def report(self, playback: Playback[ReportT], report: ReportT) -> None:
        """Hands the owner a position of ``playback``, as a block the device took reports it."""
        self._claims[playback].listener.positioned(playback, report)

    def end(self, playback: Playback[Any], ending: Ending) -> None:
        """Hands the owner the end report of ``playback``, which no longer holds the output."""
        claim = self._claims[playback]
        claim.engaged = False
        claim.listener.ended(playback, ending)

    def is_engaged(self, feed: PlaybackFeed) -> bool:
        return self._claims[feed].engaged

    def is_paused(self, feed: PlaybackFeed) -> bool:
        claim = self._claims[feed]
        return claim.engaged and claim.paused

    def pause(self, feed: PlaybackFeed) -> bool:
        return self._hold(feed, paused=True)

    def resume(self, feed: PlaybackFeed) -> bool:
        return self._hold(feed, paused=False)

    def stop(self, feed: PlaybackFeed) -> bool:
        claim = self._claims[feed]
        if not claim.engaged:
            return False

        claim.engaged = False
        claim.stopped = True
        return True

    def command(self, feed: PlaybackFeed, action: VoidCallback) -> bool:
        if not self._claims[feed].engaged:
            return False

        action()
        return True

    def fail(self, feed: PlaybackFeed, error: Exception) -> bool:
        claim = self._claims[feed]
        if not claim.engaged:
            return False

        claim.engaged = False
        claim.listener.ended(feed, Ending.failure(error))
        return True

    def _hold(self, feed: PlaybackFeed, *, paused: bool) -> bool:
        claim = self._claims[feed]
        if not claim.engaged:
            return False

        claim.paused = paused
        return True
