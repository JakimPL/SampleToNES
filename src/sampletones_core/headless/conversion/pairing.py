from typing import List

from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.headless.conversion.request import ConversionRequest
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


def describe_stem(entry: StemEntry) -> str:
    """One stem as the pairing names it: its id, the channels it occupies and how it plays them.

    The channels it bends, a count below the channels it holds and a channel driven off unit each
    add a clause, so a line states what a reader chose and leaves the usual unsaid.
    """
    settings = entry.settings
    channels = ", ".join(channel.value for channel in settings.channels)
    parts = [f"stem {entry.id} on {channels}"]
    bends = ", ".join(channel.value for channel in settings.bends)
    if bends:
        parts.append(f"bending {bends}")

    if settings.channel_cap < len(settings.channels):
        parts.append(f"{settings.channel_cap} at once")

    driven = _driven_channels(settings)
    if driven:
        parts.append(f"driving {driven}")

    return ", ".join(parts)


def _driven_channels(settings: StemSettings) -> str:
    """The channels the stem plays off unit drive, each with the level it gives them."""
    return ", ".join(
        f"{channel.value} at {settings.drives[channel]:.2f}"
        for channel in settings.channels
        if settings.drives[channel] != UNIT_DRIVE
    )


def pairing_lines(request: ConversionRequest) -> List[str]:
    """One line per source naming the stem it plays under, in the order they pair."""
    directory = request.directory
    if directory is not None:
        return [f"{directory.name}/: every recording under {describe_stem(request.stems.entries[0])}"]

    return [f"{source.name}: {describe_stem(entry)}" for source, entry in zip(request.sources, request.stems.entries)]
