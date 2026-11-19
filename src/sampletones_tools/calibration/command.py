from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "calibration"
HELP: Final[str] = (
    "measure how the program reconstructs the reference sounds and write the renders, a report and a listening page"
)
OUTPUT_HELP: Final[str] = (
    "the directory the run writes into; without it, a timestamped directory under Documents/SampleToNES/calibration"
)
CONFIG_HELP: Final[str] = "the configuration file to measure; without it, the program's default settings"
METHODS_HELP: Final[str] = "spectrum methods to measure, comma separated; without it, the suite's methods"
EXPONENTS_HELP: Final[str] = (
    "values of metric.perceptual_exponent to measure, comma separated; without it, the suite's values"
)
WEIGHTS_HELP: Final[str] = (
    "values of weights.temporal_loss_weight to measure, comma separated; without it, the suite's values"
)
CHANNELS_HELP: Final[str] = (
    "channels every variant reconstructs the synthesized sounds with, comma separated; without it, the suite's "
    "channels"
)
CATEGORIES_HELP: Final[str] = "categories of reference sounds to measure, comma separated; without it, every one"
SKIP_HELP: Final[str] = "families or categories of reference sounds to leave out, comma separated, e.g. notes"
WORKERS_HELP: Final[str] = "how many conversions run at once; without it, the configuration's general.max_workers"
RESUME_HELP: Final[str] = "take up the run in --output where it stopped, converting only the sounds it has no record of"
CORPUS_HELP: Final[str] = "a manifest of local sounds, such as NES-MDB pieces, that join the packaged reference sounds"
BOARD_HELP: Final[str] = (
    "run directories to compare on one listening page, measuring nothing; without -o the page lands in a "
    "timestamped directory under Documents/SampleToNES/calibration/pages"
)
PALETTE_HELP: Final[str] = "the palette the listening page is drawn in; without it, the application's own"
NO_OPEN_HELP: Final[str] = "leave the listening page closed, printing its link alone"
FETCH_SAMPLES_HELP: Final[str] = (
    "download the recordings the benchmark keeps for listening, each checked against its checksum, measuring nothing"
)

MEASURING_OPTIONS: Final[List[str]] = [
    "--config",
    "--methods",
    "--perceptual-exponents",
    "--temporal-weights",
    "--channels",
    "--categories",
    "--skip",
    "--workers",
    "--resume",
    "--corpus",
]


@dataclass(frozen=True)
class CalibrationArguments:
    """What a calibration run is given, as written on the command line."""

    config: Optional[Path]
    output: Optional[Path]
    methods: Optional[str]
    perceptual_exponents: Optional[str]
    temporal_weights: Optional[str]
    channels: Optional[str]
    categories: Optional[str]
    skip: Optional[str]
    workers: Optional[int]
    resume: bool
    corpus: Optional[Path]
    board: Optional[List[Path]]
    palette: Optional[str]
    open_page: bool
    fetch_samples: bool


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--config", "-c", type=Path, default=None, help=CONFIG_HELP)
    parser.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)
    parser.add_argument("--methods", type=str, default=None, help=METHODS_HELP)
    parser.add_argument("--perceptual-exponents", type=str, default=None, help=EXPONENTS_HELP)
    parser.add_argument("--temporal-weights", type=str, default=None, help=WEIGHTS_HELP)
    parser.add_argument("--channels", type=str, default=None, help=CHANNELS_HELP)
    parser.add_argument("--categories", type=str, default=None, help=CATEGORIES_HELP)
    parser.add_argument("--skip", type=str, default=None, help=SKIP_HELP)
    parser.add_argument("--workers", type=int, default=None, help=WORKERS_HELP)
    parser.add_argument("--resume", action="store_true", help=RESUME_HELP)
    parser.add_argument("--corpus", type=Path, default=None, metavar="FILE", help=CORPUS_HELP)
    parser.add_argument("--board", type=Path, nargs="+", default=None, metavar="RUN", help=BOARD_HELP)
    parser.add_argument("--palette", type=str, default=None, help=PALETTE_HELP)
    parser.add_argument("--no-open", dest="open_page", action="store_false", help=NO_OPEN_HELP)
    parser.add_argument("--fetch-samples", action="store_true", help=FETCH_SAMPLES_HELP)


def run(arguments: Namespace) -> int:
    """Runs the calibration the options describe, or builds a page over the runs they name.

    Raises:
        SystemExit: If a method, a value, a channel or a palette is unknown, a file named is missing,
            a manifest is malformed, a run cannot be resumed, a run directory holds no renders, or a
            page is asked for beside the options that measure.
    """
    given = CalibrationArguments(
        config=arguments.config,
        output=arguments.output,
        methods=arguments.methods,
        perceptual_exponents=arguments.perceptual_exponents,
        temporal_weights=arguments.temporal_weights,
        channels=arguments.channels,
        categories=arguments.categories,
        skip=arguments.skip,
        workers=arguments.workers,
        resume=arguments.resume,
        corpus=arguments.corpus,
        board=arguments.board,
        palette=arguments.palette,
        open_page=arguments.open_page,
        fetch_samples=arguments.fetch_samples,
    )

    if given.fetch_samples:
        return _fetch()

    return _compare(given) if given.board is not None else _measure(given)


def _measure(given: CalibrationArguments) -> int:
    from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
    from sampletones_core.headless.conversion.request import channels_named
    from sampletones_shared.utils.validation import describe_failure
    from sampletones_tools.calibration.config.manifest import CorpusManifest
    from sampletones_tools.calibration.config.suite import SuiteConfig
    from sampletones_tools.calibration.corpus.reference import reference_catalog
    from sampletones_tools.calibration.fingerprint import ResumeRefusedError
    from sampletones_tools.calibration.session import (
        CalibrationRequest,
        base_configuration,
        calibrate,
        default_output,
        floats_named,
        measured_categories,
        methods_named,
    )

    suite = SuiteConfig.load()
    try:
        manifest = CorpusManifest.read(given.corpus) if given.corpus is not None else None
        base = base_configuration(given.config)
        request = CalibrationRequest(
            base=base,
            output=given.output if given.output is not None else default_output(),
            methods=methods_named(given.methods, suite.methods),
            perceptual_exponents=floats_named(given.perceptual_exponents, suite.perceptual_exponents),
            temporal_weights=floats_named(given.temporal_weights, suite.temporal_weights),
            channels=channels_named(given.channels) if given.channels is not None else list(suite.channels),
            categories=measured_categories(given.categories, given.skip, reference_catalog(manifest)),
            workers=given.workers if given.workers is not None else base.general.max_workers,
            resume=given.resume,
            corpus=given.corpus,
            palette=given.palette if given.palette is not None else DEFAULT_PALETTE_NAME,
        )
    except ValueError as error:
        raise SystemExit(describe_failure(error)) from error
    except FileNotFoundError as error:
        raise SystemExit(str(error)) from error

    try:
        outcome = calibrate(request)
    except ResumeRefusedError as error:
        raise SystemExit(str(error)) from error

    print(f"Report: {outcome.report.resolve().as_uri()}")
    return _show(outcome.page, given.open_page)


def _compare(given: CalibrationArguments) -> int:
    from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
    from sampletones_tools.calibration.board.session import BoardRequest, build_board
    from sampletones_tools.calibration.session import default_page_output

    _refuse_measuring(given)
    request = BoardRequest(
        runs=list(given.board or []),
        output=given.output if given.output is not None else default_page_output(),
        palette=given.palette if given.palette is not None else DEFAULT_PALETTE_NAME,
    )
    try:
        page = build_board(request)
    except (FileNotFoundError, KeyError) as error:
        raise SystemExit(str(error)) from error

    return _show(page, given.open_page)


def _fetch() -> int:
    from urllib.error import URLError

    from sampletones_tools.calibration.config.samples import SamplesConfig
    from sampletones_tools.calibration.samples import SAMPLES_DIRECTORY, SampleChecksumError, fetch_samples

    try:
        fetched = fetch_samples(SamplesConfig.load(), SAMPLES_DIRECTORY)
    except (URLError, SampleChecksumError) as error:
        raise SystemExit(f"The samples could not be fetched: {error}") from error

    print(f"Samples: {len(fetched)} in {SAMPLES_DIRECTORY}")
    return 0


def _show(page: Path, wanted: bool) -> int:
    from sampletones_tools.calibration.board.browser import open_page

    print(f"Page: {page.resolve().as_uri()}")
    if wanted:
        open_page(page)

    return 0


def _refuse_measuring(given: CalibrationArguments) -> None:
    measuring = (
        given.config,
        given.methods,
        given.perceptual_exponents,
        given.temporal_weights,
        given.channels,
        given.categories,
        given.skip,
        given.workers,
        given.corpus,
    )
    if any(value is not None for value in measuring) or given.resume:
        named = ", ".join(MEASURING_OPTIONS)
        raise SystemExit(f"--board reads finished runs and measures nothing; it takes none of {named}.")


CALIBRATION: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
