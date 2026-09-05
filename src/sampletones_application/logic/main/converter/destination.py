from dataclasses import dataclass, replace
from pathlib import Path
from typing import AbstractSet, Optional, Self, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.converter.paths import get_output_path, group_output_path


@dataclass(frozen=True)
class Destination:
    """What a run converts and where the reconstruction it writes lands.

    The output path follows the input: a recording names the document beside it, a directory names
    the tree its batch mirrors, and a mix names the document the gathered recordings amount to.
    Deriving it in one step keeps the path the panel shows and the path the run writes the same
    answer.
    """

    input_path: Optional[Path]
    output_path: Optional[Path]
    is_file: bool

    @classmethod
    def unset(cls) -> Self:
        """The destination a converter opens with, before a reader has picked anything."""
        return cls(input_path=None, output_path=None, is_file=True)

    @property
    def reconstruction_name(self) -> str:
        """The document a single job writes, which is what a run of one is making."""
        if self.output_path is not None:
            return self.output_path.stem

        return self.input_path.stem if self.input_path is not None else ""

    def aimed_at(
        self,
        config: Config,
        input_path: Path,
        channels: AbstractSet[ChannelName],
    ) -> Self:
        """The destination a newly picked recording or directory names.

        Raises:
            FileNotFoundError: The path names nothing on disk.
            OSError: The path cannot be read.
        """
        return replace(
            self,
            input_path=input_path,
            output_path=get_output_path(config, input_path, channels),
            is_file=input_path.is_file(),
        )

    def aimed_at_mix(
        self,
        config: Config,
        sources: Tuple[Path, ...],
        channels: AbstractSet[ChannelName],
    ) -> Self:
        """The destination the recordings a mix gathers name between them.

        A mix with nobody taking part names nothing of its own, so the destination it last held
        stands until a recording joins it.
        """
        if not sources:
            return self

        return replace(self, output_path=group_output_path(config, sources, channels))

    def writing_to(self, output_path: Path) -> Self:
        """The destination a completed run wrote, which is the document a reader would open."""
        return replace(self, output_path=output_path)
