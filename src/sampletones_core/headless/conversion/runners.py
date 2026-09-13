from pathlib import Path
from typing import Final, Optional, Tuple

from tqdm import tqdm

from sampletones_core.configs import Config
from sampletones_core.headless.conversion.request import ConversionRequest
from sampletones_core.headless.library import generate_library
from sampletones_core.library import InstructionLibrary
from sampletones_core.parallelization import TaskProgress, TaskStatus
from sampletones_core.reconstructions import Reconstructor
from sampletones_core.reconstructions.converter import (
    ConversionJob,
    DirectoryConversion,
    ReconstructionConverter,
    reconstruct_job,
)
from sampletones_core.reconstructions.converter.paths import group_output_path
from sampletones_core.reconstructions.progress import ReconstructionProgress
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.logger import logger, null_logger

BAR_STEPS: Final[int] = 1000


def reconstruct(request: ConversionRequest, config: Config) -> None:
    """Builds what the request asks for: one reconstruction of the recordings, or one per file of the directory."""
    directory = request.directory
    if directory is not None:
        reconstruct_directory(directory, config, request.stems)
        return

    reconstruct_sources(request.sources, config, request.stems, request.output_path)


def reconstruct_sources(
    sources: Tuple[Path, ...],
    config: Config,
    stems: StemsConfig,
    output_path: Optional[Path],
) -> None:
    """Mixes the recordings into one reconstruction and writes it, showing the progress as a bar.

    A file already standing at the output path is kept, and the run says so.

    Args:
        sources: The recordings, one per stem of the setup.
        config: The configuration selecting the library and the matching settings.
        stems: The setup handing the channels out.
        output_path: The file written, or ``None`` for the configuration's own directory.
    """
    if output_path is None:
        output_path = group_output_path(config, sources, stems.covered_channels)

    if output_path.exists():
        logger.info(f"Reconstruction {output_path} exists, skipping")
        return

    names = ", ".join(source.name for source in sources)
    logger.info(f"Starting reconstruction of {names}")
    job = ConversionJob(sources=sources, stems=stems, output_path=output_path)
    progress_bar = tqdm(total=BAR_STEPS, desc=f"Reconstructing {output_path.stem}", unit="step")

    def on_progress(progress: ReconstructionProgress) -> bool:
        progress_bar.set_postfix_str(progress.stage)
        progress_bar.update(round(progress.fraction * BAR_STEPS) - progress_bar.n)
        return True

    try:
        reconstruct_job((Reconstructor(config, stems.covered_channels), job, on_progress))
    finally:
        progress_bar.close()

    logger.info(f"Reconstruction file saved to {output_path}")


def reconstruct_directory(
    directory: Path,
    config: Config,
    stems: StemsConfig,
) -> None:
    """Reconstructs every recording under the directory, each alone under the setup's stem.

    The library the configuration names is generated first where it is missing. The results
    mirror the directory's tree inside the configuration's reconstructions directory.

    Args:
        directory: The directory of recordings.
        config: The configuration selecting the library and the matching settings.
        stems: The one-stem setup every recording is converted under.
    """
    library = InstructionLibrary.from_config(config)
    if not library.exists(config):
        logger.warning("Library does not exist for the given configuration, generating a new library")
        generate_library(config)

    progress_bar = tqdm(total=0, desc=f"Reconstructing {directory.name}", unit="file")

    def on_start() -> None:
        progress_bar.disable = False
        logger.info(f"Starting reconstruction for directory {directory}")

    def on_completed(written: Tuple[Path, ...]) -> None:
        logger.info(f"Reconstructed {len(written)} files from {directory}")
        progress_bar.close()

    def on_progress(
        task_status: TaskStatus,
        task_progress: TaskProgress,
    ) -> None:
        progress_bar.disable = False
        total = task_progress.total
        if total and total != progress_bar.total:
            progress_bar.total = total
            progress_bar.refresh()

        delta = int(task_progress.completed) - int(progress_bar.n)
        if delta > 0:
            progress_bar.update(delta)

        if task_progress.current_item:
            progress_bar.set_description(f"{directory.name}: {task_progress.current_item}")

        if task_status in (
            TaskStatus.COMPLETED,
            TaskStatus.CANCELED,
            TaskStatus.FAILED,
        ):
            progress_bar.close()

    def on_canceled() -> None:
        logger.info("Reconstruction canceled by user")
        progress_bar.close()

    def on_error(_exception: Exception) -> None:
        progress_bar.close()

    converter = ReconstructionConverter(
        config,
        DirectoryConversion(directory=directory, stems=stems),
        logger=null_logger,
    )

    converter.set_callbacks(
        on_start=on_start,
        on_completed=on_completed,
        on_progress=on_progress,
        on_canceled=on_canceled,
        on_error=on_error,
    )

    try:
        converter.start()
        converter.wait()
    except KeyboardInterrupt:
        logger.info("Reconstruction interrupted by user")
    finally:
        progress_bar.close()
