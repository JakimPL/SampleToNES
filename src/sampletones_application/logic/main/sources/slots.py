from dataclasses import dataclass
from typing import Callable, Dict, Final, FrozenSet, Tuple

from sampletones_application.constants.sources import SettingsField
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, ordered_channels
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

SettingsReader = Callable[[StemSettings], FrozenSet[ChannelName]]
SettingsWriter = Callable[[StemSettings, FrozenSet[ChannelName]], StemSettings]
SettingsOffer = Callable[[StemSettings], FrozenSet[ChannelName]]

ALL_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())


def _channels_of(settings: StemSettings) -> FrozenSet[ChannelName]:
    return settings.channel_set


def _with_channels(
    settings: StemSettings,
    channels: FrozenSet[ChannelName],
) -> StemSettings:
    """The settings occupying ``channels``, keeping the bends that still reach one of them.

    A bend belongs to a channel the recording occupies, so narrowing the channels narrows the
    bends along with them and one gesture leaves a value the model accepts.
    """
    held = ordered_channels(channels)
    return StemSettings(channels=held, bends=ordered_channels(settings.bend_set & channels))


def _channels_offered(_settings: StemSettings) -> FrozenSet[ChannelName]:
    return ALL_CHANNELS


def _bends_of(settings: StemSettings) -> FrozenSet[ChannelName]:
    return settings.bend_set


def _bends_offered(settings: StemSettings) -> FrozenSet[ChannelName]:
    """A bend belongs to a channel the recording occupies whose hardware reads one."""
    return settings.channel_set & TONE_CHANNELS


def _with_bends(
    settings: StemSettings,
    bends: FrozenSet[ChannelName],
) -> StemSettings:
    """The settings bending ``bends``, holding each to a channel occupied whose hardware reads one."""
    reached = bends & settings.channel_set & TONE_CHANNELS
    return StemSettings(channels=settings.channels, bends=ordered_channels(reached))


@dataclass(frozen=True)
class SettingsSlot:
    """One per-recording choice, in the form every reader of it works through.

    A slot states how the choice is read from a recording's settings, how a settled value is
    written back, and which channels put it to a reader as those settings stand. The list, the
    folder fold and the settings card all work through slots, so a further choice reaches each of
    them as one more slot rather than as a field spelled out again in every layer.
    """

    field: SettingsField
    read: SettingsReader
    write: SettingsWriter
    offered: SettingsOffer

    def offers(self, settings: StemSettings, channel_name: ChannelName) -> bool:
        """Whether this choice is put to a reader on ``channel_name``, as ``settings`` stand."""
        return channel_name in self.offered(settings)

    def holds(self, settings: StemSettings, channel_name: ChannelName) -> bool:
        """Whether ``settings`` makes this choice on ``channel_name``."""
        return channel_name in self.read(settings)

    def settled(
        self,
        settings: StemSettings,
        channel_name: ChannelName,
        held: bool,
    ) -> StemSettings:
        """The settings with ``channel_name`` settled in this slot."""
        reached = self.read(settings)
        channels = reached | {channel_name} if held else reached - {channel_name}
        return self.write(settings, frozenset(channels))


CHANNEL_SLOT: Final[SettingsSlot] = SettingsSlot(
    field=SettingsField.CHANNELS,
    read=_channels_of,
    write=_with_channels,
    offered=_channels_offered,
)

BEND_SLOT: Final[SettingsSlot] = SettingsSlot(
    field=SettingsField.BENDS,
    read=_bends_of,
    write=_with_bends,
    offered=_bends_offered,
)

SETTINGS_SLOTS: Final[Tuple[SettingsSlot, ...]] = (CHANNEL_SLOT, BEND_SLOT)

SLOTS_BY_FIELD: Final[Dict[SettingsField, SettingsSlot]] = {slot.field: slot for slot in SETTINGS_SLOTS}
