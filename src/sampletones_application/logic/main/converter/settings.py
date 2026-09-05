from dataclasses import dataclass, replace
from typing import FrozenSet, Self

from sampletones_application.constants.conversion import MIN_CHANNEL_CAP
from sampletones_application.constants.output import OutputKind
from sampletones_application.logic.main.sources.slots import CHANNEL_SLOT
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


@dataclass(frozen=True)
class RunSettings:
    """The choices a run holds to, whatever it converts.

    ``joining`` is what a recording is given when it joins the setup, and a run hands out the
    channels it names: every gathered recording is narrowed to them, so this one value settles
    both what a new row starts from and what the whole run reaches. The rest name the shape of the
    run itself — what it writes, how many channels one recording may hold in a frame, and how the
    levels take turns.
    """

    joining: StemSettings
    output: OutputKind
    channel_cap: int
    hierarchy_mode: HierarchyMode

    @property
    def enabled_channels(self) -> FrozenSet[ChannelName]:
        """The channels a run hands out, which is what a joining recording holds."""
        return self.joining.channel_set

    @property
    def max_channel_cap(self) -> int:
        """The highest cap there is, which is one recording holding every channel in a frame."""
        return len(ChannelName)

    @property
    def effective_channel_cap(self) -> int:
        """The cap a run holds to, within the channels the hardware has."""
        return min(self.channel_cap, self.max_channel_cap)

    def with_joining(self, joining: StemSettings) -> Self:
        """The settings a recording joins the list with, as a reader settled them."""
        return replace(self, joining=joining)

    def with_joining_channels(self, channels: FrozenSet[ChannelName]) -> Self:
        """The settings a recording joins with, holding exactly ``channels``.

        A bend the recording carried on a channel left out goes with it, which is what keeps the
        joining settings a value the core accepts.
        """
        return replace(self, joining=CHANNEL_SLOT.write(self.joining, channels))

    @property
    def mixes(self) -> bool:
        """Several recordings are being gathered into one reconstruction."""
        return self.output.mixes

    def with_output(self, output: OutputKind) -> Self:
        """The run writing one reconstruction per gathered recording, or one from them all."""
        return replace(self, output=output)

    def with_channel_cap(self, channel_cap: int) -> Self:
        """The cap the reader asked for, held between one channel and the channels enabled."""
        return replace(self, channel_cap=min(max(channel_cap, MIN_CHANNEL_CAP), self.max_channel_cap))

    def with_hierarchy_mode(self, hierarchy_mode: HierarchyMode) -> Self:
        """The run taking its levels round by round, or one level exhausted before the next."""
        return replace(self, hierarchy_mode=hierarchy_mode)
