from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Self, Sequence, Tuple

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.constants.enums import ChannelName
from sampletones_core.data import DataModel
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.source import StemSource
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


class StemsData(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    config: StemsConfig = Field(
        ...,
        description="The stems setup the assignment was made under",
    )
    sources: List[StemSource] = Field(
        default_factory=list,
        description="Where each recording came from and what it is called, one per entry",
    )
    assignments: List[ChannelAssignment] = Field(
        ...,
        description="Per channel, the stem holding each frame",
    )

    @classmethod
    def single_entry(
        cls,
        settings: StemSettings,
        assignments: List[ChannelAssignment],
    ) -> StemsData:
        """The record of one stem converted with ``settings``, holding the frames ``assignments`` name."""
        return cls(
            config=StemsConfig.single_entry(settings),
            assignments=assignments,
        )

    @model_validator(mode="after")
    def _validate_sources_name_the_entries(self) -> Self:
        """Holds the recorded sources to the entries they belong to.

        Raises:
            ValueError: If the sources name entries other than the recorded ones, or name one
                of them twice.
        """
        if not self.sources:
            return self

        named = [source.stem_id for source in self.sources]
        if sorted(named) != sorted(self.config.entries_by_id):
            raise ValueError(
                f"The recorded sources name {sorted(named)} where the setup holds {sorted(self.config.entries_by_id)}"
            )

        return self

    @cached_property
    def assignments_by_channel(self) -> Dict[ChannelName, List[int]]:
        """The per-frame stem ids each channel carries, keyed by channel."""
        return {item.channel_name: item.stem_ids for item in self.assignments}

    @cached_property
    def sources_by_id(self) -> Dict[int, StemSource]:
        """Where each recording came from, keyed by the entry it was converted as."""
        return {source.stem_id: source for source in self.sources}

    @property
    def paths(self) -> Tuple[Path, ...]:
        """Where the recordings live, in entry order, empty once any of them is let go of.

        One unreadable recording costs the whole original, so a set the document can offer whole
        is the one every reader asks for.
        """
        located = [self.sources_by_id[entry.id].path for entry in self.config.entries if entry.id in self.sources_by_id]
        if len(located) != len(self.config.entries) or any(path is None for path in located):
            return ()

        return tuple(path for path in located if path is not None)

    def named(self, stem_id: int) -> Optional[str]:
        """What one recording is called, absent where the record names none."""
        source = self.sources_by_id.get(stem_id)
        return source.name if source is not None else None

    def with_sources(self, paths: Sequence[Path]) -> StemsData:
        """The record naming where each entry's recording came from, in entry order.

        A conversion states one path per entry, which is what the sources are read from. Handing
        it no path at all leaves the sources as they stand, so a record already naming its
        recordings keeps them.

        Raises:
            ValueError: If the paths number anything other than one per recorded entry.
        """
        if not paths:
            return self

        if len(paths) != len(self.config.entries):
            raise ValueError(
                f"The recorded sources number {len(paths)} where the setup holds {len(self.config.entries)}"
            )

        return self._with_sources(
            [StemSource.of(entry.id, Path(source)) for entry, source in zip(self.config.entries, paths)]
        )

    def detached(self) -> StemsData:
        """The record with every recording's location let go of, keeping the names it holds."""
        return self._with_sources([source.detached() for source in self.sources])

    def _with_sources(self, sources: List[StemSource]) -> StemsData:
        """This record carrying ``sources``, built afresh so its memoized views follow them."""
        return StemsData(config=self.config, sources=sources, assignments=self.assignments)
