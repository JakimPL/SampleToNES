import threading
from multiprocessing import Manager
from pathlib import Path
from typing import Any, Callable, Optional, Union

from configs.config import Config
from reconstructor.scripts import reconstruct_directory, reconstruct_single_file


class ReconstructionConverter:
    def __init__(self, config: Config) -> None:
        self.config = config

        self.thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.progress_queue: Optional[Any] = None
        self._manager: Optional[Any] = None

        self.cancelling = False
        self.running = False
        self.total_files = 0
        self.completed_files = 0
        self.current_file: Optional[str] = None
        self.cancel_flag: Optional[Any] = None
        self.target_path: Optional[Path] = None

        self._on_cancelled: Optional[Callable[[], None]] = None
        self._on_complete: Optional[Callable[[Path], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    def start(self, target_path: Path, is_file: bool) -> None:
        if self.running:
            return

        self.running = True
        self.target_path = target_path
        self.total_files = 0
        self.completed_files = 0
        self._manager = Manager()
        self.progress_queue = self._manager.Queue()
        self.cancel_flag = self._manager.Value("b", False)

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
        try:
            output_json = reconstruct_single_file(self.config, input_path, self.progress_queue, self.cancel_flag)
        except Exception as error:
            self._handle_error(error)
            return
        finally:
            self.running = False

        if not self.cancel_flag or not self.cancel_flag.value:
            if self._on_complete:
                self._on_complete(output_json)

    def _reconstruct_directory_worker(self, directory_path: Path) -> None:
        try:
            reconstruct_directory(self.config, directory_path, self.progress_queue, self.cancel_flag)
        except Exception as error:
            self._handle_error(error)
        finally:
            self.running = False

        if not self.cancel_flag or not self.cancel_flag.value:
            if self._on_complete is not None:
                self._on_complete(directory_path)

    def _handle_error(self, error: Exception) -> None:
        if self._on_error is not None:
            self._on_error(str(error))

    def cancel(self) -> None:
        if self.cancelling:
            return

        self.cancelling = True
        if self.cancel_flag:
            self.cancel_flag.value = True

        cancel_monitor = threading.Thread(target=self._wait_for_cancellation, daemon=True)
        cancel_monitor.start()

    def _wait_for_cancellation(self) -> None:
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        self.running = False
        self.cancelling = False

        if self._on_cancelled:
            self._on_cancelled()

    def is_running(self) -> bool:
        return self.running

    def is_cancelling(self) -> bool:
        return self.cancelling

    def get_progress(self) -> float:
        if self.total_files == 0:
            return 0.0
        return self.completed_files / self.total_files

    def get_current_file(self) -> Optional[str]:
        return self.current_file

    def set_callbacks(
        self,
        on_complete: Optional[Callable[[Path], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_cancelled: Optional[Callable[[], None]] = None,
    ) -> None:
        self._on_complete = on_complete
        self._on_error = on_error
        self._on_cancelled = on_cancelled
