from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter.job import ConversionJob
from sampletones_core.reconstructions.converter.paths.utils import (
    ConfigDirectories,
    get_relative_path,
    named_output_path,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.exceptions import NoFilesToProcessError


@dataclass(frozen=True)
class BatchEntry:
    """One recording a batch converts on its own, under the setup handing out its channels.

    The reconstruction lands in the folder named after the channels this recording is handed, so
    a folder holds reconstructions made with the channels its name states. ``base_directory``
    names the folder the recording was gathered from, whose tree the written reconstructions
    mirror. A recording gathered by name carries none, and its reconstruction sits directly in its
    channels' folder.
    """

    source: Path
    stems: StemsConfig
    base_directory: Optional[Path]

    @property
    def is_named(self) -> bool:
        """The reader named this recording itself, rather than the folder holding it."""
        return self.base_directory is None

    def directory(self, directories: ConfigDirectories) -> Path:
        """The folder of the channels this recording is handed, which its reconstruction lands in."""
        return directories.directory(self.stems.covered_channels)

    def output_path(self, directories: ConfigDirectories) -> Path:
        """The reconstruction this recording is written to."""
        directory = self.directory(directories)
        if self.base_directory is None:
            return named_output_path(directory, (self.source,))

        return get_relative_path(self.base_directory, self.source, directory / self.base_directory.name)


@dataclass(frozen=True)
class BatchConversion:
    """One reconstruction per recording gathered, each built from that recording alone.

    Every recording carries the channels its own row holds and is written into the folder named
    after them, so one batch writes as many folders as the setups the reader worked out. A
    recording named by the reader is written whenever the batch runs; one gathered from a folder is
    left as it stands where its own reconstruction is already written, so a repeated run over a
    folder picks up where the last one stopped and writes again the recordings whose channels
    changed since.
    """

    entries: Tuple[BatchEntry, ...]

    def destination(self, config: Config) -> Path:
        """The reconstruction a batch of one writes, or the folder holding everything a larger batch writes.

        Recordings sharing their channels share one folder, which is that folder; recordings with
        different channels fill one folder apiece, all held in the reconstructions directory.
        """
        directories = ConfigDirectories(config)
        if len(self.entries) == 1:
            return self.entries[0].output_path(directories)

        named = {entry.directory(directories) for entry in self.entries}
        if len(named) == 1:
            return named.pop()

        return directories.root

    def jobs(self, config: Config) -> List[ConversionJob]:
        """The single-source jobs this batch writes.

        Raises:
            NoFilesToProcessError: If every gathered recording is reconstructed already.
        """
        directories = ConfigDirectories(config)
        targets = ((entry, entry.output_path(directories)) for entry in self.entries)
        jobs = [
            ConversionJob(sources=(entry.source,), stems=entry.stems, output_path=output_path)
            for entry, output_path in targets
            if entry.is_named or not output_path.exists()
        ]
        if not jobs:
            raise NoFilesToProcessError("Every gathered recording is reconstructed already")

        return jobs

    def existing_targets(self, config: Config) -> Tuple[Path, ...]:
        """The reconstructions standing where a recording the reader named would be written."""
        directories = ConfigDirectories(config)
        named = (entry.output_path(directories) for entry in self.entries if entry.is_named)
        return tuple(output_path for output_path in named if output_path.is_file())
