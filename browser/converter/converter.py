import gc
import threading
from multiprocessing import Manager
from pathlib import Path
from typing import Any, Callable, Optional, Union

from configs.config import Config
from constants.browser import EXT_FILE_JSON
from reconstructor.reconstructor import Reconstructor
from reconstructor.scripts import (
    generate_config_directory_name,
    reconstruct_directory,
    reconstruct_file,
)


class ReconstructionConverter:
    def __init__(
        self,
        config: Config,
        on_complete: Optional[Callable[[Optional[Path]], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.config = config
        self.on_complete = on_complete
        self.on_error = on_error
        self.thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.running = False
        self.progress_queue: Optional[Any] = None
        self.total_files = 0
        self.completed_files = 0
        self.current_file: Optional[str] = None
        self._manager: Optional[Any] = None

    def start(self, target_path: Union[str, Path], is_file: bool) -> None:
        if self.running:
            return

        self.running = True
        target_path = Path(target_path)
        self.total_files = 0
        self.completed_files = 0
        self._manager = Manager()
        self.progress_queue = self._manager.Queue()

        if is_file:
            self.total_files = 1
            worker = self._reconstruct_file_worker
        else:
            worker = self._reconstruct_directory_worker

        self.thread = threading.Thread(target=worker, args=(target_path,), daemon=True)
        self.thread.start()

        self.monitor_thread = threading.Thread(target=self._monitor_queue, daemon=True)
        self.monitor_thread.start()

    def _monitor_queue(self) -> None:
        while self.running:
            if self.progress_queue and not self.progress_queue.empty():
                message = self.progress_queue.get()
                if message[0] == "total":
                    self.total_files = message[1]
                elif message[0] == "completed":
                    self.completed_files += 1
                    self.current_file = message[1]

    def _reconstruct_file_worker(self, input_path: Path) -> None:
        config_directory = generate_config_directory_name(self.config)
        output_directory = Path(self.config.general.output_directory) / config_directory
        output_path = output_directory / input_path.stem

        try:
            reconstructor = Reconstructor(self.config)
            reconstruct_file(reconstructor, input_path, output_path)
        except Exception as error:
            self._handle_error(error)
            return
        finally:
            self.running = False
            gc.collect()

        output_json = output_path.with_suffix(EXT_FILE_JSON)
        if self.on_complete:
            self.on_complete(output_json)

    def _reconstruct_directory_worker(self, directory_path: Path) -> None:
        try:
            reconstruct_directory(self.config, directory_path, self.progress_queue)
        except Exception as error:
            self._handle_error(error)
            return
        finally:
            self.running = False
            gc.collect()

        if self.on_complete:
            self.on_complete(None)

    def _handle_error(self, error: Exception) -> None:
        if self.on_error:
            self.on_error(str(error))

    def cancel(self) -> None:
        self.running = False

    def is_running(self) -> bool:
        return self.running

    def get_progress(self) -> float:
        if self.total_files == 0:
            return 0.0
        return self.completed_files / self.total_files

    def get_current_file(self) -> Optional[str]:
        return self.current_file
