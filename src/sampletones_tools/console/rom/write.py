from typing import NamedTuple


class VideoWrite(NamedTuple):
    """One store a program makes to the picture processor.

    Attributes:
        address: The register the store lands on: ``$2000``-``$2007``, or ``$4014`` for a sprite transfer.
        value: The byte it carries.
        cycle: The CPU cycle the store completes on, counted from the start of the frame it falls in.
        rendering: Whether the picture was being drawn when the store landed, which is when only
            vertical blank leaves the processor's memory free to write.
        warming: Whether the store fell inside the stretch after power-on in which the processor
            ignores its control, mask, scroll and address registers.
    """

    address: int
    value: int
    cycle: int
    rendering: bool
    warming: bool
