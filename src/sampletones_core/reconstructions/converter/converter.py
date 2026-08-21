from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

from sampletones_core.configs import Config
from sampletones_core.parallelization import TaskProcessor
from sampletones_shared.logger import LoggerProtocol
from sampletones_shared.logger import logger as default_logger

from ..reconstructor.reconstructor import Reconstructor
from .conversion import reconstruct_job
from .job import ConversionJob
from .plan.protocol import ConversionPlan


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

        self.current_file: Optional[str] = None

    def start(self) -> None:
        if self.running:
            self.logger.warning("Reconstruction is already running")
            return

        super().start()

    def _create_tasks(self) -> List[Any]:
        reconstructor = Reconstructor(self.config)
        self.jobs = self.plan.jobs(self.config)
        return [(reconstructor, job) for job in self.jobs]

    def _get_task_function(
        self,
    ) -> Callable[[Tuple[Reconstructor, ConversionJob]], Path]:
        return reconstruct_job

    def _process_results(self, results: List[Path]) -> Tuple[Path, ...]:
        """The reconstructions the run wrote, in job order."""
        return tuple(output_path for output_path in results if output_path.exists())

    def _notify_progress(self) -> None:
        if 0 < self.completed_tasks <= len(self.jobs):
            self.current_file = str(self.jobs[self.completed_tasks - 1].sources[0])
            self.current_item = self.current_file

        super()._notify_progress()
