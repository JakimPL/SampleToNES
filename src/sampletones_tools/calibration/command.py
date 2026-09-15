from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "calibration"
HELP: Final[str] = "measure how the program reconstructs the reference sounds and write the renders and a report"
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


@dataclass(frozen=True)
class CalibrationArguments:
    """What a calibration run is given, as written on the command line."""

    config: Optional[Path]
    output: Optional[Path]
    methods: Optional[str]
    perceptual_exponents: Optional[str]
    temporal_weights: Optional[str]
    channels: Optional[str]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--config", "-c", type=Path, default=None, help=CONFIG_HELP)
    parser.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)
    parser.add_argument("--methods", type=str, default=None, help=METHODS_HELP)
    parser.add_argument("--perceptual-exponents", type=str, default=None, help=EXPONENTS_HELP)
    parser.add_argument("--temporal-weights", type=str, default=None, help=WEIGHTS_HELP)
    parser.add_argument("--channels", type=str, default=None, help=CHANNELS_HELP)


def run(arguments: Namespace) -> int:
    """Runs the calibration the options describe.

    Raises:
        SystemExit: If a method, a value or a channel is unknown.
    """
    given = CalibrationArguments(
        config=arguments.config,
        output=arguments.output,
        methods=arguments.methods,
        perceptual_exponents=arguments.perceptual_exponents,
        temporal_weights=arguments.temporal_weights,
        channels=arguments.channels,
    )

    from sampletones_core.headless.conversion.request import channels_named
    from sampletones_shared.utils.validation import describe_failure
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
        )
    except ValueError as error:
        raise SystemExit(describe_failure(error)) from error

    report = calibrate(request)
    print(f"Report: {report.resolve().as_uri()}")
    return 0


CALIBRATION: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
