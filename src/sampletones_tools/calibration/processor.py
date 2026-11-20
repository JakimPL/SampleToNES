from functools import lru_cache
from typing import Callable, FrozenSet, List, Sequence

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.parallelization.outcome import RunCompleted
from sampletones_core.parallelization.processor import TaskProcessor
from sampletones_core.reconstructions import Reconstructor
from sampletones_shared.logger import LoggerProtocol

from .config.level import WorkingLevel
from .levels import level_reconstructor
from .referee.panel import RefereePanel, build_panel
from .runner import CalibrationRow, Conversion, evaluate_conversion

Answers = List[List[CalibrationRow]]


class CalibrationProcessor(TaskProcessor[List[CalibrationRow]]):
    """Converts a run's sounds on a pool of workers, each conversion answering with its rows.

    A worker builds a variant's reconstructor and the referees once and keeps them for every
    conversion it is handed, so a library is read once per worker and variant.
    """

    def __init__(self, conversions: Sequence[Conversion], *, workers: int, logger: LoggerProtocol) -> None:
        super().__init__(max_workers=workers, logger=logger)
        self.conversions = list(conversions)
        self.answers: Answers = []

    def _create_tasks(self) -> List[Conversion]:
        return self.conversions

    def _get_task_function(self) -> Callable[[Conversion], List[CalibrationRow]]:
        return convert_in_worker

    def _process_results(self, completed: RunCompleted[List[CalibrationRow]]) -> Answers:
        """Every conversion's rows, in the order the conversions were handed out."""
        self.answers = list(completed.results)
        return self.answers

    def _task_name(self, index: int) -> str:
        conversion = self.conversions[index]
        return f"[{conversion.variant.label}] {conversion.item.name}"


def convert_in_worker(conversion: Conversion) -> List[CalibrationRow]:
    """Converts and judges one sound with the reconstructor and the referees this worker keeps."""
    panel = _worker_panel(conversion.variant.config.library.sample_rate)
    variant = conversion.variant
    reconstructor = _worker_reconstructor(variant.config.model_dump_json(), conversion.channels, variant.level)
    return evaluate_conversion(conversion, reconstructor, panel)


@lru_cache(maxsize=None)
def _worker_reconstructor(config: str, channels: FrozenSet[ChannelName], level: WorkingLevel) -> Reconstructor:
    return level_reconstructor(Config.model_validate_json(config), channels, level)


@lru_cache(maxsize=None)
def _worker_panel(sample_rate: int) -> RefereePanel:
    return build_panel(sample_rate)
