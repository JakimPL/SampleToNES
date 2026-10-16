from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sampletones_core.audio.output.ending import EndCause, Ending


class PlaybackPhase(Enum):
    """Where a playback stands between its claim and its end report.

    A playback plays from its claim, sounding or held paused. It is ending once its end is decided and
    its report still has to go out, which the thread writing to the device sends once that thread has
    taken the playback out of the sound. It has ended once the report is out.
    """

    PLAYING = "playing"
    ENDING = "ending"
    ENDED = "ended"


@dataclass(frozen=True)
class PlaybackState:
    """A picture of a playback's lifecycle, equal for two lifecycles that answer every later event alike."""

    phase: PlaybackPhase
    paused: bool
    ending: Optional[Ending]


class PlaybackLifecycle:
    """One playback's state, which decides what it still accepts and the one end report it sends.

    Every event is answered in every phase, so whichever thread brings an event, and in whatever order
    events arrive, the playback stays in a phase it can leave by a known path. The first cause to end it
    is the one its report names, with one exception: a sound that finished and then fails to play its
    tail out ends as a failure, since the failure is what its owner has to hear. Pausing is a flag beside
    the phase, which a playback keeps for as long as it plays.

    The owner serializes the events, which is what lets a case check every order they can come in.
    """

    def __init__(self) -> None:
        self._phase = PlaybackPhase.PLAYING
        self._paused: bool = False
        self._ending: Optional[Ending] = None

    @property
    def phase(self) -> PlaybackPhase:
        return self._phase

    @property
    def state(self) -> PlaybackState:
        return PlaybackState(phase=self._phase, paused=self._paused, ending=self._ending)

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def ending(self) -> Optional[Ending]:
        """How the playback ends, from the moment its end is decided."""
        return self._ending

    @property
    def engaged(self) -> bool:
        """Whether the playback holds the output, from its claim until its end is decided."""
        return self._phase is PlaybackPhase.PLAYING

    @property
    def mixed(self) -> bool:
        """Whether the next block written holds the playback's sound."""
        return self.engaged and not self._paused

    def pause(self) -> bool:
        """Holds the playback where it stands; answers whether it was playing to be held."""
        if not self.engaged:
            return False

        self._paused = True
        return True

    def resume(self) -> bool:
        """Lets a held playback sound again; answers whether it was playing to be let go."""
        if not self.engaged:
            return False

        self._paused = False
        return True

    def accepts_commands(self) -> bool:
        """Whether a seek or a replacement still reaches the playback, which holds while it plays."""
        return self.engaged

    def stop(self) -> bool:
        """Ends the playback because its owner stopped it; answers whether the stop decided its end."""
        return self._decide(Ending.of(EndCause.STOPPED))

    def displace(self) -> bool:
        """Ends the playback because another sound took the output; answers whether that decided its end."""
        return self._decide(Ending.of(EndCause.TAKEN))

    def finish(self) -> bool:
        """Ends the playback because the device holds its last frame; answers whether that decided its end."""
        return self._decide(Ending.of(EndCause.FINISHED))

    def fail(self, error: Exception) -> bool:
        """Ends the playback with a failure; answers whether the failure is what its report names.

        A playback that finished and still waits for its tail to play out fails as well, since a tail cut
        short is what its owner has to hear about.
        """
        if self._phase is PlaybackPhase.ENDING and self._ending is not None:
            if self._ending.cause is not EndCause.FINISHED:
                return False

            self._ending = Ending.failure(error)
            return True

        return self._decide(Ending.failure(error))

    def written(self) -> bool:
        """Answers whether a block the device took reports the playback's positions, which holds while it plays."""
        return self.engaged

    def settle(self) -> Optional[Ending]:
        """Ends a playback whose end is decided, answering the ending its report names exactly once."""
        if self._phase is not PlaybackPhase.ENDING:
            return None

        self._phase = PlaybackPhase.ENDED
        return self._ending

    def _decide(self, ending: Ending) -> bool:
        if not self.engaged:
            return False

        self._phase = PlaybackPhase.ENDING
        self._ending = ending
        self._paused = False
        return True
