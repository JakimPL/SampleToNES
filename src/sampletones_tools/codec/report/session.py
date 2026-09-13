from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, Sequence, Tuple

from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.compression import PLANE_COUNT, PLANE_STATE_SIZE
from sampletones_tools.codec.report.corpus import CorpusEntry, corpus_entries
from sampletones_tools.codec.report.encoding import Encoding, encode_corpus, report_rows
from sampletones_tools.codec.report.rows import write_csv, write_markdown
from sampletones_tools.codec.report.songs import available_bytes
from sampletones_tools.corpus.build import build_corpus

CSV_FILENAME: Final[str] = "report.csv"
MARKDOWN_FILENAME: Final[str] = "report.md"


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
    rows = report_rows(entries, encodings, space)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / CSV_FILENAME
    markdown_path = output / MARKDOWN_FILENAME
    write_csv(rows, csv_path)
    write_markdown(rows, markdown_path, PLANE_COUNT * PLANE_STATE_SIZE)
    return csv_path, markdown_path


def run_report(output: Path) -> Tuple[Path, Path]:
    """Builds the synthetic corpus, compresses it under every variant and writes the report.

    Args:
        output: The directory the report is written into.

    Returns:
        Tuple[Path, Path]: The CSV table and the Markdown table.
    """
    with TemporaryDirectory() as recordings:
        corpus = build_corpus(Path(recordings))

    entries = corpus_entries(corpus.catalog, corpus.project)
    return write_report(entries, encode_corpus(entries), available_bytes(DriverImage.load()), output)
