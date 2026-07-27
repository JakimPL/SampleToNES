from typing import Callable, Final, FrozenSet, Optional

from sampletones_application.view_model.sequencer.channels import SequencerChannelsViewModel
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.utils.callbacks import CallbackMixin

ALL_CHANNELS: Final[FrozenSet[GeneratorName]] = frozenset(GeneratorName.items())
_NO_CHANNELS: Final[FrozenSet[GeneratorName]] = frozenset()


class SequencerChannelsLogic(CallbackMixin):
    """Owns which tracker channels the song player silences.

    Holds monitoring state for the open document alone, the way :class:`SequencerGridLogic`
    holds the visible frame: the project keeps every channel, so saving, export, and the
    history stack read the full song. A document transition calls :meth:`reset`, which returns
    the whole set to audible.

    Solo is derived from the same mute set rather than a flag of its own: soloing a channel
    silences the other three and remembers the set it replaced, so leaving the solo returns to
    the mix it interrupted.

    The synthesiser reads :attr:`active_channels` on every rendered row, so a change is heard
    while playback continues.
    """

    def __init__(self) -> None:
        self._muted: FrozenSet[GeneratorName] = _NO_CHANNELS
        self._muted_before_solo: Optional[FrozenSet[GeneratorName]] = None

        self.on_channels_changed: Optional[Callable[[SequencerChannelsViewModel], None]] = None

    @property
    def active_channels(self) -> FrozenSet[GeneratorName]:
        """The channels that sound, the mask the synthesiser mixes."""
        return ALL_CHANNELS - self._muted

    def build_channels(self) -> SequencerChannelsViewModel:
        return SequencerChannelsViewModel(muted=self._muted)

    def push_channels(self) -> None:
        self.call(self.on_channels_changed, self.build_channels())

    def toggle(self, generator: GeneratorName) -> None:
        """Flips one channel between audible and silent."""
        self._muted_before_solo = None
        self._apply(self._muted ^ {generator})

    def solo(self, generator: GeneratorName) -> None:
        """Silences every other channel, restoring the previous mix once ``generator`` plays alone.

        The mute set in force when the solo starts is remembered, so a second solo of the same
        channel returns to it. Editing the mute set by hand adopts that set as the state a later
        solo returns to.
        """
        others = ALL_CHANNELS - {generator}
        if self._muted == others:
            restored = self._muted_before_solo if self._muted_before_solo is not None else _NO_CHANNELS
            self._muted_before_solo = None
            self._apply(restored)
            return

        self._muted_before_solo = self._muted
        self._apply(others)

    def toggle_all(self) -> None:
        """Silences every channel while any still plays; a fully silent set restores them all.

        This is the master column's gesture. It reads as the select-all checkbox it resembles:
        the click follows the state the columns show, and it reaches muting everything — the
        tedious operation by hand — in one gesture, while returning from full silence stays one
        gesture too.
        """
        self._muted_before_solo = None
        self._apply(_NO_CHANNELS if self._muted == ALL_CHANNELS else ALL_CHANNELS)

    def unmute_all(self) -> None:
        """Returns every channel to audible from any mute set."""
        self._muted_before_solo = None
        self._apply(_NO_CHANNELS)

    def reset(self) -> None:
        """Starts a fresh listening session, the state a newly opened document is heard in."""
        self.unmute_all()

    def _apply(self, muted: FrozenSet[GeneratorName]) -> None:
        self._muted = muted
        self.push_channels()
