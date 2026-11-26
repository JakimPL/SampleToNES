from pathlib import Path
from typing import Final, List, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_shared.distribution import SAMPLETONES_VERSION
from sampletones_shared.logger import logger
from sampletones_tools.calibration.board.session import BoardRequest, build_board
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.config.manifest import CorpusManifest
from sampletones_tools.calibration.config.settings import SettingsConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.reference import reference_corpus
from sampletones_tools.calibration.corpus.writer import write_corpus
from sampletones_tools.calibration.evaluation import evaluate_variants
from sampletones_tools.calibration.fingerprint import (
    ResumeRefusedError,
    check_resumable,
    fingerprint_of,
    holds_fingerprint,
    write_fingerprint,
)
from sampletones_tools.calibration.layout import CORPUS_DIRECTORY, CSV_REPORT, MARKDOWN_REPORT
from sampletones_tools.calibration.oracle.judging import oracle_rows
from sampletones_tools.calibration.paths import SOURCE_DIRECTORIES
from sampletones_tools.calibration.referee.panel import RefereePanel, build_panel
from sampletones_tools.calibration.renders import clear_renders, holds_renders
from sampletones_tools.calibration.report import write_csv, write_markdown
from sampletones_tools.calibration.rows import CalibrationRow
from sampletones_tools.calibration.source import source_digest
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

    A request names a sweep whose variants can be built, each under a label of its own, so a sweep
    the variants cannot be built from is refused as the request is read, before the run starts.

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
    levels: List[VariantLevel] = Field(min_length=1)
    categories: List[str] = Field(min_length=1)
    workers: int = Field(ge=1)
    resume: bool
    corpus: Optional[Path]
    palette: str = DEFAULT_PALETTE_NAME

    @model_validator(mode="after")
    def _buildable_sweep(self) -> Self:
        """Refuse a sweep whose variants cannot be built.

        Such a sweep holds a set naming a setting the configuration lacks, or two variants under one
        label.

        Raises:
            ValueError: If the variants cannot be built from the sweep.
        """
        self.measured_variants()
        return self

    def measured_variants(self) -> List[CalibrationVariant]:
        """Every variant of the sweep asked for, the named sets read from the packaged settings.

        Raises:
            ValidationError: If a set of settings names a setting the configuration lacks.
            ValueError: If two variants share a label.
        """
        catalog = SettingsConfig.load().settings
        return build_variants(
            self.base,
            self.methods,
            self.perceptual_exponents,
            self.temporal_weights,
            settings={name: catalog[name] for name in self.settings},
            levels=self.levels,
        )


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

    The run claims its directory before it converts anything: a fresh run clears the renders and
    recordings an earlier run left and writes the fingerprint of what it measures, and a resumed run
    confirms the directory's fingerprint matches before it takes up the records already written. The
    referees are built before the claim, since the fingerprint holds them. The corpus is written
    next, since every conversion reads its sound from a file. Every sound written as NES frames is
    then read by the oracle, what playing its frames exactly scores (``oracle_rows``). The reports
    and the page come last, from every row and record.

    Returns:
        CalibrationOutcome: The report and the listening page the run wrote.

    Raises:
        ResumeRefusedError: If a run is resumed in a directory holding no run, or another run, or a
            fresh run is given a directory holding renders or recordings no run claimed.
    """
    sample_rate = request.base.library.sample_rate
    items = _measured_items(request)
    variants = request.measured_variants()
    panel = build_panel(sample_rate)
    _claim_directory(request, variants, items, panel)

    item_paths = write_corpus(items, request.output / CORPUS_DIRECTORY, sample_rate)
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
    rows.extend(oracle_rows(items, panel, request.output, request.base, resume=request.resume))

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


def _claim_directory(
    request: CalibrationRequest,
    variants: List[CalibrationVariant],
    items: List[CorpusItem],
    panel: RefereePanel,
) -> None:
    """Mark the output as this run's: confirm a resumed run's fingerprint, or claim the folder whole for a fresh run.

    A fresh run clears every render, record and recording an earlier run left before it writes its
    fingerprint, so the page and a later resume read this run's records alone.

    Raises:
        ResumeRefusedError: If a run is resumed in a directory holding no run, or another run, or a
            fresh run is given a directory holding renders or recordings no run claimed.
    """
    source = source_digest(SOURCE_DIRECTORIES, SAMPLETONES_VERSION)
    fingerprint = fingerprint_of(variants, items, request.channels, panel, source)
    if request.resume:
        check_resumable(request.output, fingerprint)
    else:
        _clear_earlier_run(request.output)
        write_fingerprint(request.output, fingerprint)


def _clear_earlier_run(output: Path) -> None:
    """Clear the renders and recordings of the run that claimed ``output`` before, where one did.

    A folder an earlier run claimed holds its fingerprint, so its renders and recordings are that
    run's to clear. Renders or recordings with no fingerprint beside them are files no run claimed,
    which a run leaves where they stand.

    Raises:
        ResumeRefusedError: If the folder holds renders or recordings no run claimed.
    """
    if holds_fingerprint(output):
        clear_renders(output)
    elif holds_renders(output):
        raise ResumeRefusedError(
            f"'{output}' holds files no calibration run claimed; choose another folder for the run"
        )


def _write_reports(rows: List[CalibrationRow], output: Path) -> Path:
    """Write the CSV and the markdown report into ``output``, returning the markdown one, which a reader opens."""
    write_csv(rows, output / CSV_REPORT)
    report = output / MARKDOWN_REPORT
    write_markdown(rows, report)
    return report
