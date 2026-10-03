from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, List, Optional, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.converter.job import ConversionJob
from sampletones_core.reconstructions.converter.paths.utils import (
    config_directory_path,
    get_relative_path,
    named_output_path,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.exceptions import NoFilesToProcessError


@dataclass(frozen=True)
class BatchEntry:
    """One recording a batch converts on its own, under the setup handing out its channels.

    ``base_directory`` names the folder the recording was gathered from, whose tree the written
    reconstructions mirror. A recording gathered by name carries none, and its reconstruction
    sits directly in the directory its batch writes into.
    """

    source: Path
    stems: StemsConfig
    base_directory: Optional[Path]

    @property
    def is_named(self) -> bool:
        """The reader named this recording itself, rather than the folder holding it."""
        return self.base_directory is None

    def output_path(self, directory: Path) -> Path:
        """The reconstruction this recording is written to, inside the directory its batch writes into."""
        if self.base_directory is None:
            return named_output_path(directory, (self.source,))

        return get_relative_path(self.base_directory, self.source, directory / self.base_directory.name)


@dataclass(frozen=True)
class BatchConversion:
    """One reconstruction per recording gathered, each built from that recording alone.

    Every recording carries the channels its own row holds, so one batch writes as many setups
    as the reader worked out. They all land in one directory, named after every channel the
    batch hands out, so the run fills one folder. A recording named by the reader is written
    whenever the batch runs; one gathered from a folder is left as it stands where its
    reconstruction is already written, so a repeated run over a folder picks up where the last
    one stopped.
    """

    entries: Tuple[BatchEntry, ...]

    @property
    def covered_channels(self) -> FrozenSet[ChannelName]:
        """Every channel the batch hands out between its recordings."""
        return frozenset().union(*(entry.stems.covered_channels for entry in self.entries))

    def directory(self, config: Config) -> Path:
        """The directory every recording of this batch is written into.

        Raises:
            pydantic.ValidationError: If the batch holds no recording, which hands out no channel.
        """
        return config_directory_path(config, self.covered_channels)

    def destination(self, config: Config) -> Path:
        """The reconstruction a batch of one writes, or the directory a larger batch writes into."""
        if len(self.entries) == 1:
            return self.entries[0].output_path(self.directory(config))

        return self.directory(config)

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
        if not self.entries:
            return []

        directory = self.directory(config)
        return [(entry, entry.output_path(directory)) for entry in self.entries]
