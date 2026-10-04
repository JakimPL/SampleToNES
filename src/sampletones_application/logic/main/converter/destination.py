from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional, Self

from sampletones_application.logic.main.sources.list import SourceList
from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter import ConversionPlan


@dataclass(frozen=True)
class Destination:
    """What a run converts and where the reconstruction it writes lands.

    The output path is the one the run's plan names as its destination, so the path the panel
    shows and the path the run writes are one answer.
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

    def aimed_at(self, config: Config, plan: Optional[ConversionPlan]) -> Self:
        """The destination the plan a run amounts to names.

        A run of one names the document it writes, which is what a reader converting a single file
        is looking at; a larger one names the folder holding every reconstruction it writes. A run
        with nobody taking part names nothing of its own, so the destination it last held stands
        until a recording joins it.
        """
        if plan is None:
            return self

        return replace(self, output_path=plan.destination(config))

    def named_after(self, sources: SourceList) -> Self:
        """What a run names itself by, read from the sources gathered for it.

        A setup holding one row is that row: a recording names the document it makes, a folder
        names the tree it mirrors. Several rows name none of them, so the run reads as what its
        destination says instead.
        """
        rows = sources.rows
        if len(rows) != 1:
            return replace(self, input_path=None, is_file=True)

        key = rows[0].key
        return replace(self, input_path=key.path, is_file=not key.names_folder)

    def writing_to(self, output_path: Path) -> Self:
        """The destination a completed run wrote, which is the document a reader would open."""
        return replace(self, output_path=output_path)
