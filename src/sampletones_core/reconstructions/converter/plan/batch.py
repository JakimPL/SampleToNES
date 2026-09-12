from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter.job import ConversionJob
from sampletones_core.reconstructions.converter.paths.utils import (
    config_directory_path,
    get_relative_path,
    group_output_path,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.exceptions import NoFilesToProcessError


@dataclass(frozen=True)
class BatchEntry:
    """One recording a batch converts on its own, under the setup handing out its channels.

    ``base_directory`` names the folder the recording was gathered from, whose tree the written
    reconstructions mirror. A recording gathered by name carries none, and its reconstruction
    sits directly in the directory the run's settings are named after.
    """

    source: Path
    stems: StemsConfig
    base_directory: Optional[Path]

    @property
    def is_named(self) -> bool:
        """The reader named this recording itself, rather than the folder holding it."""
        return self.base_directory is None

    def output_path(self, config: Config) -> Path:
        """The reconstruction this recording is written to."""
        channels = self.stems.covered_channels
        if self.base_directory is None:
            return group_output_path(config, (self.source,), channels)

        mirrored = config_directory_path(config, channels) / self.base_directory.name
        return get_relative_path(self.base_directory, self.source, mirrored)


@dataclass(frozen=True)
class BatchConversion:
    """One reconstruction per recording gathered, each built from that recording alone.

    Every recording carries the channels its own row holds, so one batch writes as many setups
    as the reader worked out. A recording named by the reader is written whenever the batch
    runs; one gathered from a folder is left as it stands where its reconstruction is already
    written, so a repeated run over a folder picks up where the last one stopped.
    """

    entries: Tuple[BatchEntry, ...]

    def jobs(self, config: Config) -> List[ConversionJob]:
        """The single-source jobs this batch writes.

        Raises:
            NoFilesToProcessError: If every gathered recording is reconstructed already.
        """
        jobs = [
            ConversionJob(sources=(entry.source,), stems=entry.stems, output_path=output_path)
            for entry, output_path in self._targets(config)
            if entry.is_named or not output_path.exists()
        ]
        if not jobs:
            raise NoFilesToProcessError("Every gathered recording is reconstructed already")

        return jobs

    def existing_targets(self, config: Config) -> Tuple[Path, ...]:
        """The reconstructions standing where a recording the reader named would be written."""
        return tuple(
            output_path for entry, output_path in self._targets(config) if entry.is_named and output_path.is_file()
        )

    def _targets(self, config: Config) -> List[Tuple[BatchEntry, Path]]:
        return [(entry, entry.output_path(config)) for entry in self.entries]
