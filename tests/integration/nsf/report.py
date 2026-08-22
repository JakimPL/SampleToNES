import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence, Tuple

COLUMNS: Final[Tuple[str, ...]] = (
    "corpus",
    "variant",
    "ticks",
    "bytes",
    "bytes per tick",
    "ratio",
    "ticks that fit",
    "phrases",
    "dictionary",
    "seconds",
)


@dataclass(frozen=True)
class ReportRow:
    """One corpus song measured under one variant of the codec.

    Attributes:
        corpus: The song measured.
        variant: The layers the encoding was built from.
        ticks: The ticks the song lasts.
        size: The bytes the song's data takes.
        variable: The part of ``size`` that grows with the song, the fixed tables aside.
        phrases: The phrases the dictionary holds.
        dictionary: The bytes the dictionary takes, counted within ``size``.
        seconds: How long the encoding took.
        records: The bytes the same song takes as one record per tick per channel.
        space: The program area a song is written into.
    """

    corpus: str
    variant: str
    ticks: int
    size: int
    variable: int
    phrases: int
    dictionary: int
    seconds: float
    records: int
    space: int

    @property
    def bytes_per_tick(self) -> float:
        """The bytes each tick of the song costs."""
        return self.size / self.ticks

    @property
    def ratio(self) -> float:
        """How many times smaller the song is than one record per tick per channel."""
        return self.records / self.size

    @property
    def fitting_ticks(self) -> int:
        """The ticks a song at this rate reaches before it fills the program area.

        The pitch table and the dictionary are paid once however long the song runs, so what the
        remaining space is measured against is the part that grows with the ticks.
        """
        return int((self.space - (self.size - self.variable)) * self.ticks // self.variable)

    @property
    def cells(self) -> Tuple[str, ...]:
        """The row as the report prints it, column by column."""
        return (
            self.corpus,
            self.variant,
            f"{self.ticks}",
            f"{self.size}",
            f"{self.bytes_per_tick:.3f}",
            f"{self.ratio:.2f}",
            f"{self.fitting_ticks}",
            f"{self.phrases}",
            f"{self.dictionary}",
            f"{self.seconds:.2f}",
        )


def write_csv(rows: Sequence[ReportRow], path: Path) -> None:
    """Writes the measurements as a table another tool reads.

    Args:
        rows: The measurements, in the order they are reported.
        path: Where the table is written.
    """
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow(row.cells)


def write_markdown(rows: Sequence[ReportRow], path: Path, state: int) -> None:
    """Writes the measurements as a table a reader reads.

    Args:
        rows: The measurements, in the order they are reported.
        path: Where the table is written.
        state: The zero-page bytes the decoder's plane state takes.
    """
    lines = [
        "# Compression report",
        "",
        f"Decoder state: {state} bytes of zero page.",
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "|" + "|".join("---" for _ in COLUMNS) + "|",
    ]
    lines.extend("| " + " | ".join(row.cells) + " |" for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
