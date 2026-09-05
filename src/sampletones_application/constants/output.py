from enum import StrEnum


class OutputKind(StrEnum):
    """What a run writes from the recordings a reader gathered.

    The two kinds read the same list and answer differently for it: a per-recording run converts
    every recording the list holds, writing each into a tree that mirrors the folder it came from;
    a mixed run converts the recordings into one reconstruction, which is why it holds a fixed
    number of them and the levels say which picks first.
    """

    PER_RECORDING = "per_recording"
    MIXED = "mixed"

    @property
    def mixes(self) -> bool:
        """Several recordings are being gathered into one reconstruction."""
        return self is OutputKind.MIXED
