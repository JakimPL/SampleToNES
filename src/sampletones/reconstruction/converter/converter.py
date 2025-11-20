from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

from sampletones.configs import Config
from sampletones.constants.paths import EXT_FILE_WAVE
from sampletones.exceptions import NoFilesToProcessError
from sampletones.parallelization import TaskProcessor
from sampletones.utils.logger import BaseLogger
from sampletones.utils.logger import logger as default_logger

from ..reconstructor.reconstructor import Reconstructor
from .conversion import reconstruct_file
from .paths import filter_files, get_output_path, get_relative_path


class ReconstructionConverter(TaskProcessor[Path]):
    def __init__(
        self,
        config: Config,
        input_path: Path,
        is_file: bool,
        logger: BaseLogger = default_logger,
    ) -> None:
        super().__init__(max_workers=config.general.max_workers, logger=logger)
        self.config = config.model_copy()
        self.input_path: Path = input_path
        self.is_file: bool = is_file
        self.wav_files: List[Path] = []

        self.total_files = 0
        self.completed_files = 0
        self.current_file: Optional[str] = None

    def start(self) -> None:
        if self.running:
            self.logger.warning("Reconstruction is already running")
            return

        super().start()

    def _create_tasks(self) -> List[Any]:
        reconstructor = Reconstructor(self.config)
        output_path = get_output_path(self.config, self.input_path)

        if self.is_file:
            return [(reconstructor, self.input_path, output_path)]

        self.wav_files = list(self.input_path.rglob(f"*{EXT_FILE_WAVE}"))
        self.wav_files = filter_files(self.wav_files, self.input_path, output_path)

        arguments: List[Tuple[Reconstructor, Path, Path]] = []
        for wav_file in self.wav_files:
            target_path = get_relative_path(self.input_path, wav_file, output_path)
            arguments.append((reconstructor, wav_file, target_path))

        if not arguments:
            raise NoFilesToProcessError(f"No WAV files found in {self.input_path}")

        return arguments

    def _get_task_function(self) -> Callable[[Tuple], Path]:
        return reconstruct_file

    def _process_results(self, results: List[Any]) -> Path:
        if self.is_file:
            return results[0]

        return self.input_path

    def _notify_progress(self) -> None:
        self.total_files = self.total_tasks
        self.completed_files = self.completed_tasks
        if self.completed_tasks > 0 and self.completed_tasks <= len(self.wav_files):
            self.current_file = str(self.wav_files[self.completed_tasks - 1])
            self.current_item = self.current_file

        super()._notify_progress()
