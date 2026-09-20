from typing import Protocol


class PlaneCoding(Protocol):
    """What one byte of a plane stands for: a value its register reads, and the ticks it repeats.

    A plane spends its byte on a value alone or divides it, keeping the value in part of the byte
    and counting repeats in the rest. Either way a stream is read the same way — a symbol names a
    value and the ticks that value sounds for — so the packing and the parse read a coding through
    this and leave how the division is reached to the coding itself.
    """

    @property
    def repeats(self) -> int:
        """The ticks one symbol covers at most."""

    @property
    def counts(self) -> bool:
        """Whether the byte has room to count a repeat."""

    @property
    def seeded(self) -> int:
        """The register byte the plane stands at before its first token."""

    def symbol(self, value: int, repeats: int) -> int:
        """The byte the plane writes for ``value`` sounding ``repeats`` ticks running."""

    def value(self, symbol: int) -> int:
        """The register byte ``symbol`` plays."""

    def repeated(self, symbol: int) -> int:
        """The ticks ``symbol`` covers."""

    def idles(self, plane: bytes) -> bool:
        """Whether the plane holds the value it is seeded to throughout, so it takes no stream."""
