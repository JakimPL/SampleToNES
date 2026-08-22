from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter.job import ConversionJob
from sampletones_core.reconstructions.converter.paths.utils import (
    filter_files,
    get_audio_files,
    get_output_path,
    get_relative_path,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.exceptions import NoFilesToProcessError


@dataclass(frozen=True)
class DirectoryConversion:
    """One reconstruction per audio file under a directory, each built from that file alone.

    The scan reaches every audio file below the directory and keeps those whose reconstruction
    is still to be written, so a repeated run picks up where the last one stopped. The output
    tree mirrors the input tree, and every file is converted under the same stems setup.
    """

    directory: Path
    stems: StemsConfig

    def jobs(self, config: Config) -> List[ConversionJob]:
        """The single-source jobs the directory holds.

        Raises:
            NoFilesToProcessError: If the directory holds no audio file still to be converted.
        """
        output_path = get_output_path(config, self.directory)
        audio_files = filter_files(get_audio_files(self.directory), self.directory, output_path)
        if not audio_files:
            raise NoFilesToProcessError(f"No audio files found in {self.directory}")

        return [self._job(audio_file, output_path) for audio_file in audio_files]

    def existing_targets(self, _config: Config) -> Tuple[Path, ...]:
        """The empty tuple: the scan converts what is still to be written and keeps the rest."""
        return ()

    def _job(self, audio_file: Path, output_path: Path) -> ConversionJob:
        return ConversionJob(
            sources=(audio_file,),
            stems=self.stems,
            output_path=get_relative_path(self.directory, audio_file, output_path),
        )
