from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence, Tuple

from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.compression import PLANE_COUNT, PLANE_STATE_SIZE
from sampletones_tools.codec.report.corpus import CorpusEntry, corpus_entries
from sampletones_tools.codec.report.encoding import Encoding, encode_corpus, report_rows
from sampletones_tools.codec.report.rows import report_table, write_markdown
from sampletones_tools.codec.report.songs import available_bytes
from sampletones_tools.corpus.build import build_synthetic_corpus

CSV_FILENAME: Final[str] = "report.csv"
MARKDOWN_FILENAME: Final[str] = "report.md"


@dataclass(frozen=True)
class CompressionReport:
    """What a report run measured, and the tables it wrote.

    Attributes:
        entries: The songs measured.
        encodings: Every song compressed under every variant of the codec.
        csv_path: The table another tool reads.
        markdown_path: The table a reader reads.
    """

    entries: Tuple[CorpusEntry, ...]
    encodings: Tuple[Encoding, ...]
    csv_path: Path
    markdown_path: Path


def write_report(
    entries: Sequence[CorpusEntry],
    encodings: Sequence[Encoding],
    space: int,
    output: Path,
) -> Tuple[Path, Path]:
    """Writes the measurements as a table another tool reads and a table a reader reads.

    Args:
        entries: The songs measured.
        encodings: Their encodings.
        space: The program area a song is written into.
        output: The directory the two tables are written into, created when missing.

    Returns:
        Tuple[Path, Path]: The CSV table and the Markdown table.
    """
    table = report_table(report_rows(entries, encodings, space))
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / CSV_FILENAME
    markdown_path = output / MARKDOWN_FILENAME
    table.write_csv(csv_path)
    write_markdown(table, markdown_path, PLANE_COUNT * PLANE_STATE_SIZE)
    return csv_path, markdown_path


def run_report(output: Path) -> CompressionReport:
    """Builds the synthetic corpus, compresses it under every variant and writes the report.

    Args:
        output: The directory the report is written into.

    Returns:
        CompressionReport: The songs, their encodings and the tables written.
    """
    corpus = build_synthetic_corpus()
    entries = corpus_entries(corpus.catalog, corpus.project)
    encodings = encode_corpus(entries)
    csv_path, markdown_path = write_report(entries, encodings, available_bytes(DriverImage.load()), output)
    return CompressionReport(
        entries=entries,
        encodings=encodings,
        csv_path=csv_path,
        markdown_path=markdown_path,
    )
