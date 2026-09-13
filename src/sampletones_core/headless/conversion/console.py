from typing import List

from sampletones_core.headless.conversion.request import ConversionRequest
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry


def describe_stem(entry: StemEntry) -> str:
    """One stem as the pairing names it: its id, the channels it may occupy and the ones it bends."""
    channels = ", ".join(channel.value for channel in entry.settings.channels)
    bends = ", ".join(channel.value for channel in entry.settings.bends)
    bending = f", bending {bends}" if bends else ""
    return f"stem {entry.id} on {channels}{bending}"


def pairing_lines(request: ConversionRequest) -> List[str]:
    """One line per source naming the stem it plays under, in the order they pair."""
    directory = request.directory
    if directory is not None:
        return [f"{directory.name}/: every recording under {describe_stem(request.stems.entries[0])}"]

    return [f"{source.name}: {describe_stem(entry)}" for source, entry in zip(request.sources, request.stems.entries)]
