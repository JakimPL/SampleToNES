from functools import partial
from pathlib import Path
from typing import Final, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_shared.logger import logger
from sampletones_shared.utils.text import parsed_items
from sampletones_tools.calibration.board.session import BoardRequest, build_board
from sampletones_tools.calibration.config.manifest import CorpusManifest
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.reference import reference_corpus
from sampletones_tools.calibration.corpus.writer import write_corpus
from sampletones_tools.calibration.evaluation import evaluate_variants
from sampletones_tools.calibration.fingerprint import check_resumable, fingerprint_of, write_fingerprint
from sampletones_tools.calibration.layout import CORPUS_DIRECTORY, CSV_REPORT, MARKDOWN_REPORT
from sampletones_tools.calibration.referee.factory import build_referees, build_truth_referees
from sampletones_tools.calibration.report import write_csv, write_markdown
from sampletones_tools.calibration.runner import build_variants
from sampletones_tools.runs import output_root, stamped_board_directory, stamped_run_directory

OUTPUT_ROOT: Final[Path] = output_root("calibration")
BOARD_ROOT: Final[Path] = OUTPUT_ROOT / "pages"


def methods_named(stated: Optional[str], default: Sequence[SpectrumMethod]) -> List[SpectrumMethod]:
    """The spectrum methods a run evaluates: the ones named, comma separated, or ``default``.

    Raises:
        ValueError: If a name is none of the spectrum methods.
    """
    known = ", ".join(method.value for method in SpectrumMethod)
    return parsed_items(
        stated,
        default,
        parse=SpectrumMethod,
        refusal=lambda name: f"Unknown spectrum method {name!r}; the methods are {known}.",
    )


def floats_named(stated: Optional[str], default: Sequence[float]) -> List[float]:
    """The values a sweep takes: the ones named, comma separated, or ``default``.

    Raises:
        ValueError: If a value is no number.
    """
    return parsed_items(stated, default, parse=float, refusal=lambda value: f"Not a number: {value!r}.")


def categories_named(stated: Optional[str], known: Sequence[str]) -> List[str]:
    """The categories a run measures: the ones named, comma separated, or every one ``known``.

    Raises:
        ValueError: If a name is none of the ``known`` categories.
    """
    listed = ", ".join(known)
    return parsed_items(
        stated,
        known,
        parse=partial(_known_category, known),
        refusal=lambda name: f"Unknown category {name!r}; the categories are {listed}.",
    )


def _known_category(known: Sequence[str], name: str) -> str:
    if name not in known:
        raise ValueError(name)

    return name


def measured_categories(
    stated: Optional[str],
    skipped: Optional[str],
    catalog: Sequence[Tuple[Family, str]],
) -> List[str]:
    """The categories a run measures: those named, or every one, less those ``skipped`` leaves out.

    Args:
        stated: The categories named, comma separated, or ``None`` for every one.
        skipped: The families and categories to leave out, comma separated, or ``None`` for none.
        catalog: Every category beside its family, in corpus order.

    Raises:
        ValueError: If a name is none of the categories, a skipped name none of the families or
            categories, or nothing is left to measure.
    """
    categories = [category for _, category in catalog]
    families = list(dict.fromkeys(family.value for family, _ in catalog))
    chosen = categories_named(stated, categories)
    known = [*families, *categories]
    listed = ", ".join(known)
    left_out = parsed_items(
        skipped,
        [],
        parse=partial(_known_category, known),
        refusal=lambda name: f"Unknown family or category {name!r}; the names are {listed}.",
    )
    dropped = {category for family, category in catalog if family.value in left_out or category in left_out}
    measured = [category for category in chosen if category not in dropped]
    if not measured:
        raise ValueError("The options leave no category to measure.")

    return measured


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

    A run leaves a fingerprint of what it measures, so a resumed run confirms it measures the same
    before it takes up the records already written.

    Returns:
        CalibrationOutcome: The report and the listening page the run wrote.

    Raises:
        ResumeRefusedError: If a run is resumed in a directory holding no run, or another run.
    """
    sample_rate = request.base.library.sample_rate
    manifest = CorpusManifest.read(request.corpus) if request.corpus is not None else None
    items = reference_corpus(request.base, request.categories, manifest)
    variants = build_variants(
        request.base,
        request.methods,
        request.perceptual_exponents,
        request.temporal_weights,
    )
    fingerprint = fingerprint_of(variants, items, request.channels)
    if request.resume:
        check_resumable(request.output, fingerprint)
    else:
        write_fingerprint(request.output, fingerprint)

    item_paths = write_corpus(items, request.output / CORPUS_DIRECTORY, sample_rate)
    referees = build_referees(sample_rate)
    truth_referees = build_truth_referees()
    channel_names = ", ".join(channel.value for channel in request.channels)
    logger.info(
        f"Evaluating {len(variants)} variants x {len(items)} items x {len(referees)} referees on {channel_names}"
    )
    rows = evaluate_variants(
        variants,
        items,
        item_paths,
        referees,
        truth_referees,
        request.output,
        frozenset(request.channels),
        workers=request.workers,
        resume=request.resume,
    )

    write_csv(rows, request.output / CSV_REPORT)
    report = request.output / MARKDOWN_REPORT
    write_markdown(rows, report)
    page = build_board(
        BoardRequest(
            runs=[request.output],
            output=request.output,
            palette=request.palette,
        )
    )
    return CalibrationOutcome(report=report, page=page)
