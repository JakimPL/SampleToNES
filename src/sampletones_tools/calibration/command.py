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
    "channels every variant reconstructs with, comma separated; without it, the suite's channels"
)
BOARD_HELP: Final[str] = (
    "run directories to compare on one listening page, measuring nothing; without -o the page lands in a "
    "timestamped directory under Documents/SampleToNES/calibration/pages"
)
PALETTE_HELP: Final[str] = "the palette the listening page is drawn in; without it, the application's own"
NO_OPEN_HELP: Final[str] = "leave the listening page closed, printing its link alone"

MEASURING_OPTIONS: Final[List[str]] = [
    "--config",
    "--methods",
    "--perceptual-exponents",
    "--temporal-weights",
    "--channels",
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
    board: Optional[List[Path]]
    palette: Optional[str]
    open_page: bool


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--config", "-c", type=Path, default=None, help=CONFIG_HELP)
    parser.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)
    parser.add_argument("--methods", type=str, default=None, help=METHODS_HELP)
    parser.add_argument("--perceptual-exponents", type=str, default=None, help=EXPONENTS_HELP)
    parser.add_argument("--temporal-weights", type=str, default=None, help=WEIGHTS_HELP)
    parser.add_argument("--channels", type=str, default=None, help=CHANNELS_HELP)
    parser.add_argument("--board", type=Path, nargs="+", default=None, metavar="RUN", help=BOARD_HELP)
    parser.add_argument("--palette", type=str, default=None, help=PALETTE_HELP)
    parser.add_argument("--no-open", dest="open_page", action="store_false", help=NO_OPEN_HELP)


def run(arguments: Namespace) -> int:
    """Runs the calibration the options describe, or builds a page over the runs they name.

    Raises:
        SystemExit: If a method, a value, a channel or a palette is unknown, a run directory holds
            no renders, or a page is asked for beside the options that measure.
    """
    given = CalibrationArguments(
        config=arguments.config,
        output=arguments.output,
        methods=arguments.methods,
        perceptual_exponents=arguments.perceptual_exponents,
        temporal_weights=arguments.temporal_weights,
        channels=arguments.channels,
        board=arguments.board,
        palette=arguments.palette,
        open_page=arguments.open_page,
    )

    return _compare(given) if given.board is not None else _measure(given)


def _measure(given: CalibrationArguments) -> int:
    from sampletones_core.headless.conversion.request import channels_named
    from sampletones_shared.utils.validation import describe_failure
    from sampletones_tools.calibration.board.palette import DEFAULT_PALETTE
    from sampletones_tools.calibration.config.suite import SuiteConfig
    from sampletones_tools.calibration.session import (
        CalibrationRequest,
        base_configuration,
        calibrate,
        default_output,
        floats_named,
        methods_named,
    )

    suite = SuiteConfig.load()
    try:
        request = CalibrationRequest(
            base=base_configuration(given.config),
            output=given.output if given.output is not None else default_output(),
            methods=methods_named(given.methods, suite.methods),
            perceptual_exponents=floats_named(given.perceptual_exponents, suite.perceptual_exponents),
            temporal_weights=floats_named(given.temporal_weights, suite.temporal_weights),
            channels=channels_named(given.channels) if given.channels is not None else list(suite.channels),
            palette=given.palette if given.palette is not None else DEFAULT_PALETTE,
        )
    except ValueError as error:
        raise SystemExit(describe_failure(error)) from error

    outcome = calibrate(request)
    print(f"Report: {outcome.report.resolve().as_uri()}")
    return _show(outcome.page, given.open_page)


def _compare(given: CalibrationArguments) -> int:
    from sampletones_tools.calibration.board.palette import DEFAULT_PALETTE
    from sampletones_tools.calibration.board.session import BoardRequest, build_board
    from sampletones_tools.calibration.session import default_page_output

    _refuse_measuring(given)
    request = BoardRequest(
        runs=list(given.board or []),
        output=given.output if given.output is not None else default_page_output(),
        palette=given.palette if given.palette is not None else DEFAULT_PALETTE,
    )
    try:
        page = build_board(request)
    except (FileNotFoundError, KeyError) as error:
        raise SystemExit(str(error)) from error

    return _show(page, given.open_page)


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
    )
    if any(value is not None for value in measuring):
        named = ", ".join(MEASURING_OPTIONS)
        raise SystemExit(f"--board reads finished runs and measures nothing; it takes none of {named}.")


CALIBRATION: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
