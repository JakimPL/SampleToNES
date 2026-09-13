from pathlib import Path
from typing import Final, List, Optional, Self, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator
from tqdm import tqdm

from sampletones_core.configs import Config
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    bending_channels,
    ordered_channels,
)
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
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_shared.logger import logger, null_logger
from sampletones_shared.utils.serialization import load_json

BAR_STEPS: Final[int] = 1000
CHANNEL_SEPARATOR: Final[str] = ","


def channels_named(stated: Optional[str]) -> List[ChannelName]:
    """The channels a run hands out: the ones named, comma separated, or the usual three.

    Raises:
        ValueError: If a name is none of the channels the hardware has.
    """
    if stated is None:
        return list(DEFAULT_CHANNELS)

    names = [name.strip() for name in stated.split(CHANNEL_SEPARATOR) if name.strip()]
    channels: List[ChannelName] = []
    for name in names:
        try:
            channels.append(ChannelName(name))
        except ValueError as error:
            known = ", ".join(channel.value for channel in ChannelName)
            raise ValueError(f"Unknown channel {name!r}; the channels are {known}.") from error

    return channels


def classic_setup(channels: Sequence[ChannelName]) -> StemsConfig:
    """The setup a single-source conversion runs under: one stem over the channels it was given."""
    ordered = ordered_channels(frozenset(channels))
    return StemsConfig.single_entry(ordered, bending_channels(ordered))


def load_stems(path: Path) -> StemsConfig:
    """The stems setup a JSON file holds, validated the way the ``.stn`` record is.

    Raises:
        TypeError: If the file holds anything other than a mapping.
        ValueError: If the mapping is no stems setup.
    """
    loaded = load_json(path)
    if not isinstance(loaded, dict):
        raise TypeError(f"Stems file {path} must hold a mapping, got {type(loaded).__name__}")

    return StemsConfig.model_validate(loaded)


def describe_stem(entry: StemEntry) -> str:
    """One stem as the pairing names it: its id, the channels it may occupy and the ones it bends."""
    channels = ", ".join(channel.value for channel in entry.settings.channels)
    bends = ", ".join(channel.value for channel in entry.settings.bends)
    bending = f", bending {bends}" if bends else ""
    return f"stem {entry.id} on {channels}{bending}"


class ConversionRequest(BaseModel):
    """What a headless conversion is asked for: the sources, the stems setup and where the result goes.

    The i-th source plays under the i-th entry of the setup. One directory stands for every
    recording under it, each converted alone under the setup's one stem, into the
    configuration's reconstructions directory.

    Attributes:
        sources: The recordings, or one directory of them.
        stems: The setup handing the channels out.
        output_path: The file the reconstruction of the recordings is written to, or ``None``
            for the configuration's own directory.
    """

    model_config = ConfigDict(frozen=True)

    sources: Tuple[Path, ...] = Field(min_length=1)
    stems: StemsConfig
    output_path: Optional[Path]

    @property
    def directory(self) -> Optional[Path]:
        """The one directory the request converts file by file, or ``None`` for recordings."""
        if len(self.sources) == 1 and self.sources[0].is_dir():
            return self.sources[0]

        return None

    @model_validator(mode="after")
    def _sources_are_recordings_or_one_directory(self) -> Self:
        """Raises:
        ValueError: If a directory stands among several sources.
        """
        if self.directory is None and any(source.is_dir() for source in self.sources):
            raise ValueError("Sources are recordings, or one directory alone.")

        return self

    @model_validator(mode="after")
    def _entries_pair_with_sources(self) -> Self:
        """Raises:
        ValueError: If the setup holds a different number of stems than there are sources.
        """
        entries = len(self.stems.entries)
        if self.directory is not None and entries != 1:
            raise ValueError(f"A directory is converted file by file under one stem; the setup holds {entries}.")

        if self.directory is None and entries != len(self.sources):
            raise ValueError(
                f"{len(self.sources)} sources for {entries} stems; a setup pairs one stem with each source, in order."
            )

        return self

    @model_validator(mode="after")
    def _output_names_the_one_file(self) -> Self:
        """Raises:
        ValueError: If an output path is given for a directory, whose reconstructions land in
            the configuration's directory.
        """
        if self.directory is not None and self.output_path is not None:
            raise ValueError(
                "A directory's reconstructions land in the configuration's reconstructions directory; "
                "an output path names the one file recordings are mixed into."
            )

        return self

    def pairing(self) -> List[str]:
        """One line per source naming the stem it plays under, in the order they pair."""
        directory = self.directory
        if directory is not None:
            return [f"{directory.name}/: every recording under {describe_stem(self.stems.entries[0])}"]

        return [f"{source.name}: {describe_stem(entry)}" for source, entry in zip(self.sources, self.stems.entries)]


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
