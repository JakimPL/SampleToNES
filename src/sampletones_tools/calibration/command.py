from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command
from sampletones_shared.options import add_config_option

NAME: Final[str] = "calibration"
HELP: Final[str] = "score the reconstruction corpus under candidate configurations"
OUTPUT_HELP: Final[str] = (
    "the directory the run writes into; without it, a timestamped directory under Documents/SampleToNES/calibration"
)
METHODS_HELP: Final[str] = "spectrum methods to evaluate, comma separated; without it fft and cqt"
EXPONENTS_HELP: Final[str] = "values of metric.perceptual_exponent to evaluate, comma separated; without it 1.0"
WEIGHTS_HELP: Final[str] = (
    "values of weights.temporal_loss_weight to evaluate, comma separated; without it the base blend"
)
CHANNELS_HELP: Final[str] = (
    "channels every variant reconstructs with, comma separated; without it pulse1, triangle and noise"
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
    add_config_option(parser)
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

    from sampletones_core.headless.config import load_config
    from sampletones_core.headless.conversion.request import channels_named
    from sampletones_shared.utils.validation import describe_failure
    from sampletones_tools.calibration.session import (
        BASE_BLEND,
        DEFAULT_PERCEPTUAL_EXPONENTS,
        CalibrationRequest,
        calibrate,
        default_output,
        floats_named,
        methods_named,
    )

    try:
        request = CalibrationRequest(
            base=load_config(given.config),
            output=given.output if given.output is not None else default_output(),
            methods=methods_named(given.methods),
            perceptual_exponents=floats_named(given.perceptual_exponents, DEFAULT_PERCEPTUAL_EXPONENTS),
            temporal_weights=floats_named(given.temporal_weights, BASE_BLEND),
            channels=channels_named(given.channels),
        )
    except ValueError as error:
        raise SystemExit(describe_failure(error)) from error

    calibrate(request)
    return 0


CALIBRATION: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
