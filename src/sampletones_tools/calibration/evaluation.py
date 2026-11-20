from pathlib import Path
from typing import Dict, Final, FrozenSet, List, Sequence, Tuple

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
from .runner import CalibrationRow, CalibrationVariant, Conversion, evaluate_conversion, recorded_rows

IN_PROCESS_WORKERS: Final[int] = 1
PROGRESS_UNIT: Final[str] = "sound"


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

    Every variant's library is made ready first, so workers only read it. One worker converts in
    this process; more convert on a pool, each worker keeping its own reconstructors and referees.
    A resumed run takes the rows of every conversion that left a record, and converts the rest.

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

    conversions = [
        Conversion(
            variant=variant,
            item=item,
            position=position,
            paths=item_paths[item.name],
            stems=item.stems.config if item.stems is not None else None,
            channels=item.channels if item.channels is not None else channels,
            run_directory=run_directory,
        )
        for variant in variants
        for position, item in enumerate(items)
    ]
    recorded = _recorded(conversions) if resume else {}
    pending = [conversion for index, conversion in enumerate(conversions) if index not in recorded]
    logger.info(f"Converting {len(pending)} of {len(conversions)} sounds on {workers} worker(s)")
    answers = iter(
        _convert_here(pending, panel) if workers == IN_PROCESS_WORKERS else _convert_on_pool(pending, workers)
    )
    rows: List[CalibrationRow] = []
    for index in range(len(conversions)):
        rows.extend(recorded[index] if index in recorded else next(answers))

    return rows


def _recorded(conversions: Sequence[Conversion]) -> Dict[int, List[CalibrationRow]]:
    """The rows of every conversion a record stands for, by the conversion's place in the run."""
    recorded: Dict[int, List[CalibrationRow]] = {}
    for index, conversion in enumerate(conversions):
        record = read_record(conversion.run_directory, conversion.variant.label, conversion.item.name)
        if record is not None:
            recorded[index] = recorded_rows(record)

    return recorded


def _convert_here(conversions: Sequence[Conversion], panel: RefereePanel) -> List[List[CalibrationRow]]:
    reconstructors: Dict[Tuple[str, FrozenSet[ChannelName]], Reconstructor] = {}
    answers: List[List[CalibrationRow]] = []
    for conversion in tqdm(conversions, desc="Calibrating", unit=PROGRESS_UNIT):
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
    if not conversions:
        return []

    processor = CalibrationProcessor(conversions, workers=workers, logger=logger)
    progress = tqdm(total=len(conversions), desc="Calibrating", unit=PROGRESS_UNIT)

    def on_progress(_status: TaskStatus, reached: TaskProgress) -> None:
        progress.update(reached.completed - progress.n)

    processor.on_progress = on_progress
    try:
        processor.start()
        processor.wait()
    finally:
        progress.close()

    return processor.answers
