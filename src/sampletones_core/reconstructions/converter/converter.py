from pathlib import Path
from typing import Any, Callable, FrozenSet, List, Optional, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.parallelization import TaskProcessor
from sampletones_shared.logger import LoggerProtocol
from sampletones_shared.logger import logger as default_logger

from ..progress import ReconstructionReporter
from ..reconstructor.reconstructor import Reconstructor
from .conversion import reconstruct_job
from .job import ConversionJob
from .plan.protocol import ConversionPlan
from .progress import JobReporter


class ReconstructionConverter(TaskProcessor[Path]):
    """Runs a conversion plan's jobs across a pool of worker processes.

    The plan is resolved once the run starts, on the monitor thread, so a plan that scans a
    directory does its reading there. Every job is then built by one worker, and the run
    reports the reconstructions it wrote.
    """

    def __init__(
        self,
        config: Config,
        plan: ConversionPlan,
        logger: LoggerProtocol = default_logger,
    ) -> None:
        super().__init__(max_workers=config.general.max_workers, logger=logger)
        self.config = config.model_copy()
        self.plan: ConversionPlan = plan
        self.jobs: List[ConversionJob] = []

    def start(self) -> None:
        if self.running:
            self.logger.warning("Reconstruction is already running")
            return

        super().start()

    def _create_tasks(self) -> List[Any]:
        """One task per job, sharing the reconstructor the whole run's channels are built for."""
        self.jobs = self.plan.jobs(self.config)
        reconstructor = Reconstructor(self.config, self._covered_channels())
        return [(reconstructor, job, JobReporter(self._task_reporter(index))) for index, job in enumerate(self.jobs)]

    def _covered_channels(self) -> FrozenSet[ChannelName]:
        """Every channel the jobs hand out, which is what the run builds generators for."""
        return frozenset(channel_name for job in self.jobs for channel_name in job.stems.covered_channels)

    def _get_task_function(
        self,
    ) -> Callable[[Tuple[Reconstructor, ConversionJob, ReconstructionReporter]], Path]:
        return reconstruct_job

    def _process_results(self, results: List[Path]) -> Tuple[Path, ...]:
        """The reconstructions the run wrote, in job order."""
        return tuple(output_path for output_path in results if output_path.exists())

    def _notify_progress(self) -> None:
        self.current_item = self._running_source()
        super()._notify_progress()

    def _running_source(self) -> Optional[str]:
        """The recording the job the run has been working on longest is reading.

        Jobs are answered in the order they were handed out, so the first one the run has yet to
        count is the earliest still under way — and once every job is counted, the last one is
        what the run finished on.
        """
        if not self.jobs:
            return None

        index = min(self.completed_tasks, len(self.jobs) - 1)
        return str(self.jobs[index].sources[0])
