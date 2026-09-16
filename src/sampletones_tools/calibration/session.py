from pathlib import Path
from typing import Final, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_shared.logger import logger
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS
from sampletones_shared.utils.text import listed_items
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.corpus.synthesis import build_corpus
from sampletones_tools.calibration.corpus.writer import write_corpus
from sampletones_tools.calibration.layout import CORPUS_DIRECTORY, CSV_REPORT, MARKDOWN_REPORT
from sampletones_tools.calibration.referee.factory import build_referees
from sampletones_tools.calibration.report import write_csv, write_markdown
from sampletones_tools.calibration.runner import build_variants, evaluate_variants
from sampletones_tools.runs import stamped_run_directory

OUTPUT_ROOT: Final[Path] = USER_PATH_DOCUMENTS / "calibration"


def methods_named(stated: Optional[str], default: Sequence[SpectrumMethod]) -> List[SpectrumMethod]:
    """The spectrum methods a run evaluates: the ones named, comma separated, or ``default``.

    Raises:
        ValueError: If a name is none of the spectrum methods.
    """
    if stated is None:
        return list(default)

    methods: List[SpectrumMethod] = []
    for name in listed_items(stated):
        try:
            methods.append(SpectrumMethod(name))
        except ValueError as error:
            known = ", ".join(method.value for method in SpectrumMethod)
            raise ValueError(f"Unknown spectrum method {name!r}; the methods are {known}.") from error

    return methods


def floats_named(stated: Optional[str], default: Sequence[float]) -> List[float]:
    """The values a sweep takes: the ones named, comma separated, or ``default``.

    Raises:
        ValueError: If a value is no number.
    """
    if stated is None:
        return list(default)

    values: List[float] = []
    for value in listed_items(stated):
        try:
            values.append(float(value))
        except ValueError as error:
            raise ValueError(f"Not a number: {value!r}.") from error

    return values


def base_configuration(path: Optional[Path]) -> Config:
    """The configuration a run measures: the file named, or the program's packaged defaults.

    A run with no file measures the same settings on every machine, whatever the application has
    saved, so its figures compare with any other such run.
    """
    return Config.load(path) if path is not None else Config()


def default_output() -> Path:
    """A timestamped run directory under the user's calibration documents."""
    return stamped_run_directory(OUTPUT_ROOT)


class CalibrationRequest(BaseModel):
    """What a calibration run is asked for: the base configuration, the sweep and where it writes.

    Attributes:
        base: The configuration every value the sweep leaves untouched comes from.
        output: The directory the corpus and the reports are written into.
        methods: The spectrum methods evaluated.
        perceptual_exponents: The values of ``metric.perceptual_exponent`` evaluated.
        temporal_weights: The values of ``weights.temporal_loss_weight`` evaluated; empty keeps
            the base blend.
        channels: The channels every variant reconstructs with.
    """

    model_config = ConfigDict(frozen=True)

    base: Config
    output: Path
    methods: List[SpectrumMethod] = Field(min_length=1)
    perceptual_exponents: List[float] = Field(min_length=1)
    temporal_weights: List[float]
    channels: List[ChannelName] = Field(min_length=1)


def calibrate(request: CalibrationRequest) -> Path:
    """Reconstructs the corpus under every variant, scores it, and writes the renders and the reports.

    Returns:
        Path: The markdown report, which sits in the run directory beside the renders.
    """
    request.output.mkdir(parents=True, exist_ok=True)

    sample_rate = request.base.library.sample_rate
    items = build_corpus(sample_rate, config=CorpusConfig.load())
    item_paths = write_corpus(items, request.output / CORPUS_DIRECTORY, sample_rate)
    referees = build_referees(sample_rate)
    variants = build_variants(
        request.base,
        request.methods,
        request.perceptual_exponents,
        request.temporal_weights,
    )

    channel_names = ", ".join(channel.value for channel in request.channels)
    logger.info(
        f"Evaluating {len(variants)} variants x {len(items)} items x {len(referees)} referees on {channel_names}"
    )
    rows = evaluate_variants(
        variants,
        items,
        item_paths,
        referees,
        request.output,
        frozenset(request.channels),
    )

    write_csv(rows, request.output / CSV_REPORT)
    report = request.output / MARKDOWN_REPORT
    write_markdown(rows, report)
    return report
