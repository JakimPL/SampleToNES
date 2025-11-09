import threading
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

from configs.config import Config
from constants.browser import EXT_FILE_JSON, EXT_FILE_WAV
from reconstructor.reconstructor import Reconstructor
from reconstructor.scripts import (
    filter_files,
    get_output_directory,
    get_relative_path,
    reconstruct_file,
)
from utils.parallelization.processor import TaskProcessor

ReconstructionArguments = Tuple[Reconstructor, Path, Path]


def reconstruct_file_wrapper(arguments: ReconstructionArguments) -> None:
    reconstructor, input_path, output_path = arguments
    reconstruct_file(reconstructor, input_path, output_path)


class ReconstructionConverter(TaskProcessor[Path]):
    def __init__(self, config: Config) -> None:
        super().__init__(max_workers=config.general.max_workers)
        self.config = config
        self.input_path: Optional[Path] = None
        self.is_file: bool = False
        self.wav_files: List[Path] = []

        self.total_files = 0
        self.completed_files = 0
        self.current_file: Optional[str] = None

    def start(self, target_path: Path, is_file: bool) -> None:
        if self.running:
            return

        self.running = True
        self.input_path = target_path
        self.is_file = is_file

        self.monitor_thread = threading.Thread(target=self._run_tasks, daemon=True)
        self.monitor_thread.start()

    def _create_tasks(self) -> List[Any]:
        assert self.input_path is not None, "Input path must be set before creating tasks"
        reconstructor = Reconstructor(self.config)
        output_directory = get_output_directory(self.config)

        if self.is_file:
            output_path = output_directory / self.input_path.stem
            output_path = output_path.with_suffix(EXT_FILE_JSON)
            return [(reconstructor, self.input_path, output_path)]

        self.wav_files = list(self.input_path.rglob(f"*{EXT_FILE_WAV}"))
        self.wav_files = filter_files(self.wav_files, self.input_path, output_directory)

        if not self.wav_files:
            raise ValueError(f"No WAV files found in directory: {self.input_path}")

        arguments: List[ReconstructionArguments] = []
        for wav_file in self.wav_files:
            output_path = get_relative_path(self.input_path, wav_file, output_directory)
            arguments.append((reconstructor, wav_file, output_path))

        return arguments

    def _get_task_function(self) -> Callable[[ReconstructionArguments], None]:
        return reconstruct_file_wrapper

    def _process_results(self, results: List[Any]) -> Path:
        if not self.input_path:
            raise ValueError("Target path not set")

        if self.is_file:
            return results[0]

        return self.input_path

    def get_current_file(self) -> Optional[str]:
        return self.current_file

    def _notify_progress(self) -> None:
        self.total_files = self.total_tasks
        self.completed_files = self.completed_tasks
        if self.completed_tasks > 0 and self.completed_tasks <= len(self.wav_files):
            self.current_file = str(self.wav_files[self.completed_tasks - 1])

        super()._notify_progress()
