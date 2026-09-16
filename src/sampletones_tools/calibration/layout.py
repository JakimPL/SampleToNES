from typing import Final, Sequence

from sampletones_core.constants.enums import ChannelName

CORPUS_DIRECTORY: Final[str] = "corpus"
RECORDINGS_DIRECTORY: Final[str] = "recordings"
RENDERS_DIRECTORY: Final[str] = "renders"
CSV_REPORT: Final[str] = "report.csv"
MARKDOWN_REPORT: Final[str] = "report.md"

CHANNEL_SEPARATOR: Final[str] = "+"
MIX_NAME: Final[str] = "mix"


def combination_name(channels: Sequence[ChannelName]) -> str:
    """The file name a render of exactly these channels is written under.

    The channels are named in the order they are given, joined by ``CHANNEL_SEPARATOR``, so a page
    that knows which channels it wants spells the same name the run wrote.
    """
    return CHANNEL_SEPARATOR.join(channel.value for channel in channels)
