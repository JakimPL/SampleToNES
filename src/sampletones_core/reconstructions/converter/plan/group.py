from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter.job import ConversionJob
from sampletones_core.reconstructions.converter.paths.utils import group_output_path
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig


@dataclass(frozen=True)
class GroupConversion:
    """One reconstruction from the recordings given, mixed together under one stems setup.

    One source is the classic conversion and several are the stems case; both amount to the
    same single job, which is what lets one conversion path serve them.
    """

    sources: Tuple[Path, ...]
    stems: StemsConfig

    def jobs(self, config: Config) -> List[ConversionJob]:
        return [
            ConversionJob(
                sources=self.sources,
                stems=self.stems,
                output_path=self._output_path(config),
            )
        ]

    def existing_targets(self, config: Config) -> Tuple[Path, ...]:
        """The one file this conversion writes, where it already stands."""
        output_path = self._output_path(config)
        return (output_path,) if output_path.is_file() else ()

    def _output_path(self, config: Config) -> Path:
        return group_output_path(config, self.sources)
