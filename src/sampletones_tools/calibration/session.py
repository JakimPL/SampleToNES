from pathlib import Path
from typing import Final, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_shared.logger import logger
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS
from sampletones_shared.utils.text import listed_items
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.corpus.synthesis import build_corpus
from sampletones_tools.calibration.corpus.writer import write_corpus
from sampletones_tools.calibration.referee.factory import build_referees
from sampletones_tools.calibration.report import write_csv, write_markdown
from sampletones_tools.calibration.runner import build_variants, evaluate_variants
from sampletones_tools.runs import stamped_run_directory

DEFAULT_METHODS: Final[Tuple[SpectrumMethod, ...]] = (SpectrumMethod.FFT, SpectrumMethod.CQT)
DEFAULT_PERCEPTUAL_EXPONENTS: Final[Tuple[float, ...]] = (1.0,)
BASE_BLEND: Final[Tuple[float, ...]] = ()
OUTPUT_DIRECTORY: Final[str] = "calibration"
CORPUS_DIRECTORY: Final[str] = "corpus"
CSV_REPORT: Final[str] = "report.csv"
MARKDOWN_REPORT: Final[str] = "report.md"


def methods_named(stated: Optional[str]) -> List[SpectrumMethod]:
    """The spectrum methods a run evaluates: the ones named, comma separated, or FFT and CQT.

    Raises:
        ValueError: If a name is none of the spectrum methods.
    """
    if stated is None:
        return list(DEFAULT_METHODS)

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


def default_output() -> Path:
    """A timestamped run directory under the user's calibration documents."""
    return stamped_run_directory(USER_PATH_DOCUMENTS / OUTPUT_DIRECTORY)


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

    def pinned_base(self) -> Config:
        """The base configuration reconstructing with the channels the run pins."""
        generation = self.base.generation.model_copy(update={"channels": self.channels})
        return self.base.model_copy(update={"generation": generation})


def calibrate(request: CalibrationRequest) -> Path:
    """Reconstructs the corpus under every variant, scores it with every referee and writes the reports.

    Returns:
        Path: The directory holding the corpus, ``report.csv`` and ``report.md``.
    """
    base = request.pinned_base()
    request.output.mkdir(parents=True, exist_ok=True)

    sample_rate = base.library.sample_rate
    items = build_corpus(sample_rate, config=CorpusConfig.load())
    item_paths = write_corpus(items, request.output / CORPUS_DIRECTORY, sample_rate)
    referees = build_referees(sample_rate)
    variants = build_variants(
        base,
        request.methods,
        request.perceptual_exponents,
        request.temporal_weights,
    )

    channel_names = ", ".join(channel.value for channel in request.channels)
    logger.info(
        f"Evaluating {len(variants)} variants x {len(items)} items x {len(referees)} referees on {channel_names}"
    )
    rows = evaluate_variants(variants, items, item_paths, referees)

    write_csv(rows, request.output / CSV_REPORT)
    write_markdown(rows, request.output / MARKDOWN_REPORT)
    logger.info(f"Report written to {request.output}")
    return request.output
