from pathlib import Path
from typing import Final, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_shared.logger import logger
from sampletones_tools.calibration.board.session import BoardRequest, build_board
from sampletones_tools.calibration.config.level import WorkingLevel
from sampletones_tools.calibration.config.manifest import CorpusManifest
from sampletones_tools.calibration.config.settings import SettingsConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.reference import reference_corpus
from sampletones_tools.calibration.corpus.writer import write_corpus
from sampletones_tools.calibration.evaluation import evaluate_variants
from sampletones_tools.calibration.fingerprint import check_resumable, fingerprint_of, write_fingerprint
from sampletones_tools.calibration.layout import CORPUS_DIRECTORY, CSV_REPORT, MARKDOWN_REPORT
from sampletones_tools.calibration.referee.panel import build_panel
from sampletones_tools.calibration.report import write_csv, write_markdown
from sampletones_tools.calibration.rows import CalibrationRow
from sampletones_tools.calibration.variants import CalibrationVariant, build_variants
from sampletones_tools.runs import output_root, stamped_board_directory, stamped_run_directory

OUTPUT_ROOT: Final[Path] = output_root("calibration")
BOARD_ROOT: Final[Path] = OUTPUT_ROOT / "pages"


def base_configuration(path: Optional[Path]) -> Config:
    """The configuration a run measures: the file named, or the program's packaged defaults.

    A run with no file measures the same settings on every machine, whatever the application has
    saved, so its figures compare with any other such run.
    """
    return Config.load(path) if path is not None else Config()


def default_output() -> Path:
    """A timestamped run directory under the user's calibration documents."""
    return stamped_run_directory(OUTPUT_ROOT)


def default_page_output() -> Path:
    """A timestamped page directory under the user's calibration documents."""
    return stamped_board_directory(BOARD_ROOT)


class CalibrationRequest(BaseModel):
    """What a calibration run is asked for: the base configuration, the sweep and where it writes.

    Attributes:
        base: The configuration every value the sweep leaves untouched comes from.
        output: The directory the corpus and the reports are written into.
        methods: The spectrum methods evaluated.
        perceptual_exponents: The values of ``metric.perceptual_exponent`` evaluated.
        temporal_weights: The values of ``weights.temporal_loss_weight`` evaluated; empty keeps
            the base blend.
        channels: The channels every variant reconstructs the synthesized sounds with.
        settings: The named sets of settings measured beside the base.
        levels: The levels the sounds are matched at.
        categories: The categories of reference sounds measured.
        workers: How many conversions run at once.
        resume: Whether the run takes up a run already in ``output`` where it stopped.
        corpus: A manifest of local sounds that join the packaged ones, or ``None``.
        palette: The name of the palette the run's listening page is drawn in.
    """

    model_config = ConfigDict(frozen=True)

    base: Config
    output: Path
    methods: List[SpectrumMethod] = Field(min_length=1)
    perceptual_exponents: List[float] = Field(min_length=1)
    temporal_weights: List[float]
    channels: List[ChannelName] = Field(min_length=1)
    settings: List[str]
    levels: List[WorkingLevel] = Field(min_length=1)
    categories: List[str] = Field(min_length=1)
    workers: int = Field(ge=1)
    resume: bool
    corpus: Optional[Path]
    palette: str = DEFAULT_PALETTE_NAME


class CalibrationOutcome(BaseModel):
    """What a calibration run leaves behind for a reader.

    Attributes:
        report: The markdown report, which sits in the run directory beside the renders.
        page: The listening page, the file a reader opens to hear what the run made.
    """

    model_config = ConfigDict(frozen=True)

    report: Path
    page: Path


def calibrate(request: CalibrationRequest) -> CalibrationOutcome:
    """Reconstructs the corpus under every variant, scores it, and writes the renders, reports and page.

    The run claims its directory before it converts anything: a fresh run writes the fingerprint of
    what it measures, and a resumed run confirms the directory's fingerprint matches before it takes
    up the records already written. The corpus is written next, since every conversion reads its
    sound from a file. The reports and the page come last, from every row and record.

    Returns:
        CalibrationOutcome: The report and the listening page the run wrote.

    Raises:
        ResumeRefusedError: If a run is resumed in a directory holding no run, or another run.
    """
    sample_rate = request.base.library.sample_rate
    items = _measured_items(request)
    variants = _measured_variants(request)
    _claim_directory(request, variants, items)

    item_paths = write_corpus(items, request.output / CORPUS_DIRECTORY, sample_rate)
    panel = build_panel(sample_rate)
    channel_names = ", ".join(channel.value for channel in request.channels)
    logger.info(f"Evaluating {len(variants)} variants x {len(items)} items on {channel_names}")
    rows = evaluate_variants(
        variants,
        items,
        item_paths,
        panel,
        request.output,
        frozenset(request.channels),
        workers=request.workers,
        resume=request.resume,
    )

    report = _write_reports(rows, request.output)
    page = build_board(
        BoardRequest(
            runs=[request.output],
            output=request.output,
            palette=request.palette,
        )
    )
    return CalibrationOutcome(report=report, page=page)


def _measured_items(request: CalibrationRequest) -> List[CorpusItem]:
    """The reference sounds of the categories asked for, the manifest's own among them."""
    manifest = CorpusManifest.read(request.corpus) if request.corpus is not None else None
    return reference_corpus(request.base, request.categories, manifest)


def _measured_variants(request: CalibrationRequest) -> List[CalibrationVariant]:
    """Every variant of the sweep asked for, the named sets read from the packaged settings."""
    catalog = SettingsConfig.load().settings
    return build_variants(
        request.base,
        request.methods,
        request.perceptual_exponents,
        request.temporal_weights,
        settings={name: catalog[name] for name in request.settings},
        levels=request.levels,
    )


def _claim_directory(request: CalibrationRequest, variants: List[CalibrationVariant], items: List[CorpusItem]) -> None:
    """Mark the output as this run's: confirm a resumed run's fingerprint, or write a fresh run's.

    Raises:
        ResumeRefusedError: If a run is resumed in a directory holding no run, or another run.
    """
    fingerprint = fingerprint_of(variants, items, request.channels)
    if request.resume:
        check_resumable(request.output, fingerprint)
    else:
        write_fingerprint(request.output, fingerprint)


def _write_reports(rows: List[CalibrationRow], output: Path) -> Path:
    """Write the CSV and the markdown report into ``output``, returning the markdown one, which a reader opens."""
    write_csv(rows, output / CSV_REPORT)
    report = output / MARKDOWN_REPORT
    write_markdown(rows, report)
    return report
