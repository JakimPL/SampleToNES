from pathlib import Path
from typing import Optional

from tqdm import tqdm

from sampletones.configs import Config
from sampletones.library import Library
from sampletones.parallelization import TaskProgress, TaskStatus
from sampletones.reconstruction import Reconstructor
from sampletones.reconstruction.converter import (
    ReconstructionConverter,
    get_output_path,
)
from sampletones.reconstruction.converter import reconstruct_file as _reconstruct_file
from sampletones.utils.logger import logger, null_logger

from .application import run_application
from .library import generate_library


def reconstruct_file(input_path: Path, config: Config, output_path: Optional[Path] = None) -> None:
    if output_path is None:
        output_path = get_output_path(config, input_path)

    if output_path.exists():
        logger.info(f"Reconstructing file {input_path} exists, skipping")
        return

    if input_path.is_dir():
        raise IsADirectoryError(f"Expected a file path, got directory path: {input_path}")

    logger.info(f"Starting reconstruction for file {input_path}")
    reconstructor = Reconstructor(config)
    _reconstruct_file((reconstructor, input_path, output_path))
    logger.info(f"Reconstruction file saved to {output_path}")


def reconstruct_directory(input_path: Path, config: Config, output_path: Optional[Path] = None) -> None:
    if output_path is None:
        output_path = get_output_path(config, input_path)

    if not input_path.is_dir():
        raise NotADirectoryError(f"Expected a directory path, got file path: {input_path}")

    library = Library.from_config(config)
    if not library.exists(config):
        logger.warning(f"Library does not exist for the given configuration, generating a new library")
        generate_library(config)

    converter = ReconstructionConverter(
        config,
        logger=null_logger,
    )

    progress_bar = tqdm(total=0, desc=f"Reconstructing {input_path.name}", unit="file")

    def on_start() -> None:
        progress_bar.disable = False
        logger.info(f"Starting reconstruction for directory {input_path}")

    def on_completed(path: Path) -> None:
        logger.info(f"Reconstruction directory saved to {output_path}")
        progress_bar.close()

    def on_progress(task_status: TaskStatus, task_progress: TaskProgress) -> None:
        progress_bar.disable = False
        total = task_progress.total
        if total and total != progress_bar.total:
            progress_bar.total = total
            progress_bar.refresh()

        delta = int(task_progress.completed) - int(progress_bar.n)
        if delta > 0:
            progress_bar.update(delta)

        if task_progress.current_item:
            progress_bar.set_description(f"{input_path.name}: {task_progress.current_item}")

        if task_status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
            progress_bar.close()

    def on_cancelled() -> None:
        logger.info("Reconstruction cancelled by user")
        progress_bar.close()

    def on_error(exception: Exception) -> None:
        progress_bar.close()

    converter.set_callbacks(
        on_start=on_start,
        on_completed=on_completed,
        on_progress=on_progress,
        on_cancelled=on_cancelled,
        on_error=on_error,
    )

    try:
        converter.start(input_path, is_file=False)
        converter.wait()
    except KeyboardInterrupt:
        logger.info("Reconstruction interrupted by user")
    finally:
        progress_bar.close()


def load_reconstruction(reconstruction_path: Path, config_path: Optional[Path] = None) -> None:
    raise NotImplementedError("Library reconstruction is not yet implemented")

    run_application(
        config_path=config_path,
        reconstruction_path=reconstruction_path,
    )
