from typing import Tuple

from tqdm import tqdm

from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.library import (
    InstructionLibrary,
    InstructionLibraryData,
    InstructionLibraryKey,
    LibraryState,
)
from sampletones_core.library.creator import InstructionsLibraryCreator
from sampletones_core.parallelization import TaskProgress, TaskStatus
from sampletones_shared.logger import logger, null_logger


def ensure_library(config: Config) -> None:
    """Prepares the instruction library a conversion under ``config`` searches.

    A library this build reads is used as it stands. A library built by another version is rebuilt
    in its place, and a missing one is generated.

    Args:
        config: The configuration selecting the library.

    Raises:
        KeyboardInterrupt: If the generation is interrupted, so the conversion stops with it.
    """
    window = Window.from_config(config)
    library = InstructionLibrary.from_config(config)
    key = library.create_key(config, window)
    match library.state(key):
        case LibraryState.CURRENT:
            return
        case LibraryState.OUTDATED:
            logger.info(f"Library {key.filename} was built by another version, rebuilding it")
        case LibraryState.MISSING:
            logger.info(f"Library {key.filename} is missing, generating it")

    generate_library(config)


def generate_library(config: Config) -> None:
    """Generates the instruction library for ``config`` and writes it over any file in its place.

    Args:
        config: The configuration the library is built for.

    Raises:
        KeyboardInterrupt: If the generation is interrupted.
    """
    window = Window.from_config(config)
    library = InstructionLibrary.from_config(config)
    key = library.create_key(config, window)

    creator = InstructionsLibraryCreator(config, window=window, logger=null_logger)

    progress_bar = tqdm(total=0, desc="Generating library", unit="instruction", disable=False)

    def on_start() -> None:
        logger.info(f"Starting library generation for key {key}")

    def on_completed(
        result: Tuple[InstructionLibraryKey, InstructionLibraryData],
    ) -> None:
        key, library_data = result
        library.save_data(key, library_data)
        logger.info(f"Library {key.filename} generated successfully")
        progress_bar.close()

    def on_progress(
        task_status: TaskStatus,
        _task_progress: TaskProgress,
    ) -> None:
        total = creator.total_instructions
        if total and total != progress_bar.total:
            progress_bar.total = total
            progress_bar.refresh()

        delta = int(creator.completed_instructions) - int(progress_bar.n)
        if delta > 0:
            progress_bar.update(delta)

        if task_status in (
            TaskStatus.COMPLETED,
            TaskStatus.CANCELED,
            TaskStatus.FAILED,
        ):
            progress_bar.close()

    def on_canceled() -> None:
        logger.info("Library generation canceled by user")
        progress_bar.close()

    def on_error(_exception: Exception) -> None:
        progress_bar.close()

    creator.set_callbacks(
        on_start=on_start,
        on_completed=on_completed,
        on_progress=on_progress,
        on_canceled=on_canceled,
        on_error=on_error,
    )

    try:
        creator.start()
        creator.wait()
    except KeyboardInterrupt:
        logger.info("Library generation interrupted by user")
        raise
    finally:
        progress_bar.close()
