from pathlib import Path
from typing import Dict, Final, FrozenSet, Iterator, List, Sequence, Tuple

from tqdm import tqdm

from sampletones_core.constants.enums import ChannelName
from sampletones_core.headless.library import ensure_library
from sampletones_core.parallelization.task import TaskProgress, TaskStatus
from sampletones_core.reconstructions import Reconstructor
from sampletones_shared.logger import logger

from .corpus.item import CorpusItem
from .levels import level_reconstructor
from .processor import CalibrationProcessor
from .referee.panel import RefereePanel
from .renders import read_record
from .rows import CalibrationRow, recorded_rows
from .runner import Conversion, evaluate_conversion
from .variants import CalibrationVariant

IN_PROCESS_WORKERS: Final[int] = 1
PROGRESS_LABEL: Final[str] = "Calibrating"
PROGRESS_UNIT: Final[str] = "sound"

ReconstructorKey = Tuple[str, FrozenSet[ChannelName]]


def evaluate_variants(
    variants: List[CalibrationVariant],
    items: List[CorpusItem],
    item_paths: Dict[str, Tuple[Path, ...]],
    panel: RefereePanel,
    run_directory: Path,
    channels: FrozenSet[ChannelName],
    *,
    workers: int,
    resume: bool,
) -> List[CalibrationRow]:
    """
    Convert every reference sound under every variant and gather the rows their judgments read.

    Every variant's library is made ready first, in this process, so workers only read it. A resumed
    run takes the rows of every conversion that left a record, and converts the rest. The rows come
    back in the run's order whichever way each conversion was reached, so a resumed run reports as a
    whole one does.

    Args:
        variants: Labeled configurations to evaluate.
        items: Corpus items, carrying their family and category.
        item_paths: The written WAV files per corpus item name, one per stem of a sound held as stems.
        panel: The referees judging each reconstruction in this process.
        run_directory: The directory the run writes its renders and recordings into.
        channels: The channels a sound is converted over when it names none of its own.
        workers: How many conversions run at once.
        resume: Whether conversions that left a record are taken from it.

    Returns:
        One row per (variant, item, referee, reading), in variant order and then corpus order.
    """
    for variant in variants:
        ensure_library(variant.config)

    conversions = _run_conversions(variants, items, item_paths, channels, run_directory)
    recorded = _recorded(conversions) if resume else {}
    pending = [conversion for index, conversion in enumerate(conversions) if index not in recorded]
    logger.info(f"Converting {len(pending)} of {len(conversions)} sounds on {workers} worker(s)")
    answers = iter(_convert(pending, panel, workers))
    return _in_run_order(len(conversions), recorded, answers)


def _run_conversions(
    variants: Sequence[CalibrationVariant],
    items: Sequence[CorpusItem],
    item_paths: Dict[str, Tuple[Path, ...]],
    channels: FrozenSet[ChannelName],
    run_directory: Path,
) -> List[Conversion]:
    """Every conversion of the run, variant by variant and each in corpus order, which is the run's order."""
    return [
        Conversion(
            variant=variant,
            item=item,
            position=position,
            paths=item_paths[item.name],
            run_channels=channels,
            run_directory=run_directory,
        )
        for variant in variants
        for position, item in enumerate(items)
    ]


def _recorded(conversions: Sequence[Conversion]) -> Dict[int, List[CalibrationRow]]:
    """The rows of every conversion a record stands for, by the conversion's place in the run."""
    recorded: Dict[int, List[CalibrationRow]] = {}
    for index, conversion in enumerate(conversions):
        record = read_record(conversion.run_directory, conversion.variant.label, conversion.item.name)
        if record is not None:
            recorded[index] = recorded_rows(record)

    return recorded


def _in_run_order(
    count: int,
    recorded: Dict[int, List[CalibrationRow]],
    answers: Iterator[List[CalibrationRow]],
) -> List[CalibrationRow]:
    """The rows of ``count`` conversions in run order: a recorded one's from its record, the others' in turn."""
    rows: List[CalibrationRow] = []
    for index in range(count):
        rows.extend(recorded[index] if index in recorded else next(answers))

    return rows


def _convert(conversions: Sequence[Conversion], panel: RefereePanel, workers: int) -> List[List[CalibrationRow]]:
    """Every conversion's rows, in the order given.

    One worker converts in this process with ``panel``. More convert on a pool of processes, each
    building its own reconstructors and referees.
    """
    if workers == IN_PROCESS_WORKERS:
        return _convert_in_process(conversions, panel)

    return _convert_on_pool(conversions, workers)


def _convert_in_process(conversions: Sequence[Conversion], panel: RefereePanel) -> List[List[CalibrationRow]]:
    """Every conversion's rows, converted here, one reconstructor built per variant and channels and kept."""
    reconstructors: Dict[ReconstructorKey, Reconstructor] = {}
    answers: List[List[CalibrationRow]] = []
    for conversion in tqdm(conversions, desc=PROGRESS_LABEL, unit=PROGRESS_UNIT):
        key = (conversion.variant.label, conversion.channels)
        if key not in reconstructors:
            reconstructors[key] = level_reconstructor(
                conversion.variant.config,
                conversion.channels,
                conversion.variant.level,
            )

        answers.append(evaluate_conversion(conversion, reconstructors[key], panel))

    return answers


def _convert_on_pool(conversions: Sequence[Conversion], workers: int) -> List[List[CalibrationRow]]:
    """Every conversion's rows, converted on a pool of ``workers`` processes, the progress shown as they finish."""
    if not conversions:
        return []

    processor = CalibrationProcessor(conversions, workers=workers, logger=logger)
    progress = tqdm(total=len(conversions), desc=PROGRESS_LABEL, unit=PROGRESS_UNIT)

    def on_progress(_status: TaskStatus, reached: TaskProgress) -> None:
        progress.update(reached.completed - progress.n)

    processor.on_progress = on_progress
    try:
        processor.start()
        processor.wait()
    finally:
        progress.close()

    return processor.answers
