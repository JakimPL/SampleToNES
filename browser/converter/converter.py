import threading
from pathlib import Path
from typing import Any, Callable, List, Optional

from configs.config import Config
from utils.parallelization.processor import TaskProcessor


def reconstruct_single_file_task(args) -> Path:
    config, input_path = args
    from reconstructor.scripts import reconstruct_single_file

    return reconstruct_single_file(config, input_path, progress_queue=None, cancel_flag=None)


def reconstruct_file_task(args) -> str:
    config, input_path, directory, output_directory = args
    from reconstructor.reconstructor import Reconstructor
    from reconstructor.scripts import reconstruct_file

    reconstructor = Reconstructor(config)
    relative_path = input_path.relative_to(directory)
    output_path = output_directory / relative_path
    reconstruct_file(reconstructor, input_path, output_path)

    return str(input_path)


class ReconstructionConverter(TaskProcessor[Path]):
    def __init__(self, config: Config) -> None:
        super().__init__(max_workers=config.general.max_workers)
        self.config = config
        self.target_path: Optional[Path] = None
        self.is_file: bool = False
        self.wav_files: List[Path] = []

        self.total_files = 0
        self.completed_files = 0
        self.current_file: Optional[str] = None

    def start(self, target_path: Path, is_file: bool) -> None:
        if self.running:
            return

        self.running = True
        self.target_path = target_path
        self.is_file = is_file

        self.monitor_thread = threading.Thread(target=self._run_tasks, daemon=True)
        self.monitor_thread.start()

    def _create_tasks(self) -> List[Any]:
        from constants.browser import EXT_FILE_WAV
        from reconstructor.scripts import generate_config_directory_name

        if not self.target_path:
            raise ValueError("Target path not set")

        if self.is_file:
            return [(self.config, self.target_path)]

        if not self.target_path.exists():
            raise FileNotFoundError(f"Directory does not exist: {self.target_path}")

        if not self.target_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.target_path}")

        config_directory = generate_config_directory_name(self.config)
        output_directory = Path(self.config.general.output_directory) / config_directory / self.target_path.name
        self.wav_files = list(self.target_path.rglob(f"*{EXT_FILE_WAV}"))

        if not self.wav_files:
            raise ValueError(f"No WAV files found in directory: {self.target_path}")

        return [(self.config, wav_file, self.target_path, output_directory) for wav_file in self.wav_files]

    def _get_task_function(self) -> Callable:
        if self.is_file:
            return reconstruct_single_file_task
        return reconstruct_file_task

    def _process_results(self, results: List[Any]) -> Path:
        if not self.target_path:
            raise ValueError("Target path not set")

        if self.is_file:
            return results[0]
        return self.target_path

    def get_current_file(self) -> Optional[str]:
        return self.current_file

    def _notify_progress(self) -> None:
        self.total_files = self.total_tasks
        self.completed_files = self.completed_tasks
        if self.completed_tasks > 0 and self.completed_tasks <= len(self.wav_files):
            self.current_file = str(self.wav_files[self.completed_tasks - 1])

        super()._notify_progress()
