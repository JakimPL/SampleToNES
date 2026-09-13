from __future__ import annotations

from typing import Final, NamedTuple


class Finding(NamedTuple):
    """What one hypothesis reaches in one encoding.

    Attributes:
        targeted: The bytes the hypothesis acts upon, as the encoding writes them today.
        saving: The bytes it would spare under the pricing the hypothesis states.
    """

    targeted: int
    saving: int

    def __add__(self, other: object) -> Finding:
        if not isinstance(other, Finding):
            return NotImplemented

        return Finding(self.targeted + other.targeted, self.saving + other.saving)


NOTHING: Final[Finding] = Finding(0, 0)
