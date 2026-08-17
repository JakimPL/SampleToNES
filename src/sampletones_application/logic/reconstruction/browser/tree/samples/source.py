from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True, order=True)
class SampleSource:
    """The audio a set of reconstructions was made from, as its folder and name within a configuration.

    Two configuration directories reconstructing one audio file mirror the same source subtree, so
    the relative folder and the audio name together gather the variants of that audio.
    """

    directory_parts: Tuple[str, ...]
    name: str
