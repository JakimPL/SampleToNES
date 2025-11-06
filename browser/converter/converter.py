import gc
import threading
from pathlib import Path
from typing import Callable, Optional, Union

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
        self.running = False
        self.should_cancel = False

    def start(self, target_path: Union[str, Path], is_file: bool) -> None:
        if self.running:
            return

        self.running = True
        self.should_cancel = False
        target_path = Path(target_path)

        worker = self._reconstruct_file_worker if is_file else self._reconstruct_directory_worker
        self.thread = threading.Thread(target=worker, args=(target_path,), daemon=True)
        self.thread.start()

    def _reconstruct_file_worker(self, input_path: Path) -> None:
        config_directory = generate_config_directory_name(self.config)
        output_directory = Path(self.config.general.output_directory) / config_directory
        output_path = output_directory / input_path.stem

        try:
            reconstructor = Reconstructor(self.config)
        except Exception as error:
            self._handle_error(error)
            return
        finally:
            self.running = False
            gc.collect()

        try:
            reconstruct_file(reconstructor, input_path, output_path)
        except KeyboardInterrupt:
            raise
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
            reconstruct_directory(self.config, directory_path)
        except Exception as error:
            self._handle_error(error)
            return
        finally:
            self.running = False
            gc.collect()

        if not self.should_cancel and self.on_complete:
            self.on_complete(None)

    def _handle_error(self, error: Exception) -> None:
        if self.on_error:
            self.on_error(str(error))

    def cancel(self) -> None:
        self.should_cancel = True

    def is_running(self) -> bool:
        return self.running

    def get_progress(self) -> float:
        return 0.0

    def get_current_file(self) -> Optional[str]:
        return None
