import argparse
from datetime import datetime
from pathlib import Path
from typing import Final

from sampletones_core.calibration.config.corpus import CorpusConfig
from sampletones_core.calibration.corpus.synthesis import build_corpus
from sampletones_core.calibration.corpus.writer import write_corpus
from sampletones_core.calibration.referee.factory import build_referees
from sampletones_core.calibration.report import write_csv, write_markdown
from sampletones_core.calibration.runner import build_variants, evaluate_variants
from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_GENERATORS, GeneratorName
from sampletones_shared.logger import logger

DEFAULT_OUTPUT_ROOT: Final[Path] = Path.home() / "Documents" / "SampleToNES" / "calibration"
DEFAULT_METHODS: Final[str] = "fft,cqt"
DEFAULT_PERCEPTUAL_EXPONENTS: Final[str] = "1.0"
DEFAULT_GENERATOR_NAMES: Final[str] = ",".join(generator.value for generator in DEFAULT_GENERATORS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct the calibration corpus and score it with referees.")
    parser.add_argument("--config", type=Path, default=None, help="Base configuration path.")
    parser.add_argument("--output", type=Path, default=None, help="Output directory of the run.")
    parser.add_argument("--methods", type=str, default=DEFAULT_METHODS, help="Comma-separated spectrum methods.")
    parser.add_argument(
        "--perceptual-exponents",
        type=str,
        default=DEFAULT_PERCEPTUAL_EXPONENTS,
        help="Comma-separated values of metric.perceptual_exponent.",
    )
    parser.add_argument(
        "--temporal-weights",
        type=str,
        default="",
        help="Comma-separated values of weights.temporal_loss_weight; empty keeps the base blend.",
    )
    parser.add_argument(
        "--generators",
        type=str,
        default=DEFAULT_GENERATOR_NAMES,
        help="Comma-separated channel generators every variant reconstructs with.",
    )
    arguments = parser.parse_args()

    generators = [GeneratorName(name.strip()) for name in arguments.generators.split(",") if name.strip()]
    if not generators:
        parser.error("--generators requires at least one generator name")

    base = Config.load(arguments.config) if arguments.config else Config.default()
    base = base.model_copy(
        update={"generation": base.generation.model_copy(update={"generators": generators})},
    )
    output = arguments.output or DEFAULT_OUTPUT_ROOT / datetime.now().strftime("run-%Y%m%d-%H%M%S")
    output.mkdir(parents=True, exist_ok=True)

    methods = [method.strip() for method in arguments.methods.split(",") if method.strip()]
    exponents = [float(value) for value in arguments.perceptual_exponents.split(",") if value.strip()]
    temporal_weights = [float(value) for value in arguments.temporal_weights.split(",") if value.strip()]

    sample_rate = base.library.sample_rate
    items = build_corpus(sample_rate, config=CorpusConfig.load())
    item_paths = write_corpus(items, output / "corpus", sample_rate)
    referees = build_referees(sample_rate)
    variants = build_variants(base, methods, exponents, temporal_weights)

    channel_names = ", ".join(generator.value for generator in generators)
    logger.info(
        f"Evaluating {len(variants)} variants x {len(items)} items x {len(referees)} referees on {channel_names}"
    )
    rows = evaluate_variants(variants, items, item_paths, referees)

    write_csv(rows, output / "report.csv")
    write_markdown(rows, output / "report.md")
    logger.info(f"Report written to {output}")


if __name__ == "__main__":
    main()
