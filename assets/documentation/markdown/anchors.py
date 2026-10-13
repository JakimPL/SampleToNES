import re
from typing import Dict, Final

FORMATTING: Final[re.Pattern[str]] = re.compile(r"[`*]")
PUNCTUATION: Final[re.Pattern[str]] = re.compile(r"[^\w\s-]")


def heading_anchor(heading: str) -> str:
    """The fragment GitHub gives a heading: punctuation dropped, every remaining space a hyphen."""
    text = FORMATTING.sub("", heading).strip().lower()
    return PUNCTUATION.sub("", text).replace(" ", "-")


class HeadingAnchors:
    """The anchors of one page's headings, each unique, as GitHub numbers a repeated one.

    A heading whose anchor an earlier heading already took gains ``-1``, then ``-2``, so every
    heading on a page has a fragment of its own.
    """

    def __init__(self) -> None:
        self._taken: Dict[str, int] = {}

    def claim(self, heading: str) -> str:
        anchor = heading_anchor(heading)
        repeats = self._taken.get(anchor)
        self._taken[anchor] = 0 if repeats is None else repeats + 1
        return anchor if repeats is None else f"{anchor}-{repeats + 1}"
