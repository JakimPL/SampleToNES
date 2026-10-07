from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import AbstractSet, Dict, FrozenSet, List, Optional, Self, Sequence, Tuple

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
    sources: Tuple[StemSource, ...] = Field(
        default_factory=tuple,
        description="Where each recording came from and what it is called, one per entry",
    )
    assignments: Tuple[ChannelAssignment, ...] = Field(
        ...,
        description="Per channel, the stem holding each frame",
    )
    scale: Optional[float] = Field(
        ...,
        gt=0,
        description="The factor the conversion divided every recording by, absent where it went unmeasured",
    )

    @classmethod
    def single_entry(
        cls,
        settings: StemSettings,
        assignments: List[ChannelAssignment],
        scale: Optional[float],
    ) -> StemsData:
        """The record of one stem converted with ``settings``, holding the frames ``assignments`` name."""
        return cls(
            config=StemsConfig.single_entry(settings),
            assignments=tuple(assignments),
            scale=scale,
        )

    @model_validator(mode="after")
    def _validate_an_unmeasured_scale_holds_one_recording(self) -> Self:
        """Holds a record stating no scale to the one recording such a record can carry.

        A conversion measures the scale of the whole set it reads. A document written before the
        scale was recorded holds one recording, which its own peak scales exactly as the
        conversion did, and a lone recording stays on the record for good.

        Raises:
            ValueError: If a record stating no scale names other than one recording.
        """
        if self.scale is None and len(self.config.entries) != 1:
            raise ValueError(f"A record stating no scale names {len(self.config.entries)} recordings")

        return self

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
    def assignments_by_channel(self) -> Dict[ChannelName, Tuple[int, ...]]:
        """The per-frame stem ids each channel carries, keyed by channel."""
        return {item.channel_name: item.stem_ids for item in self.assignments}

    @cached_property
    def holding_stem_ids(self) -> FrozenSet[int]:
        """The recorded entries holding a frame on some channel.

        A rest and a frame the reader wrote answer to no entry, so neither counts toward any.
        """
        held = frozenset(stem_id for item in self.assignments for stem_id in item.stem_ids)
        return held & frozenset(self.config.entries_by_id)

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
        """The record with every recording's location let go of, keeping the names it holds.

        A record holding no location is returned as it stands.
        """
        if all(source.path is None for source in self.sources):
            return self

        return self._with_sources([source.detached() for source in self.sources])

    def with_assignments(self, assignments: List[ChannelAssignment]) -> StemsData:
        """The record naming ``assignments`` as the owners of every frame, the setup and sources kept."""
        return self._rebuilt(
            config=self.config,
            sources=self.sources,
            assignments=assignments,
        )

    def without_entries(self, stem_ids: AbstractSet[int]) -> StemsData:
        """The record with the entries ``stem_ids`` names gone, together with their sources.

        A level the entries leave empty goes with them, and the ids of the entries that stay are
        left alone, so the owners the record names keep naming the same recordings.

        Args:
            stem_ids: The entries that leave.

        Returns:
            StemsData: The record of the entries that stay.
        """
        return self._rebuilt(
            config=self.config.without_entries(stem_ids),
            sources=[source for source in self.sources if source.stem_id not in stem_ids],
            assignments=self.assignments,
        )

    def settled(self, playing: AbstractSet[ChannelName]) -> StemsData:
        """The record answering for the channels in play, and naming the recordings that hold a frame.

        A channel resting through every frame stands by and describes no frame, so the record
        lets go of the owners it named there, whatever left the channel silent. A recording holding
        no frame on any channel then leaves the record, its source and its place in the hierarchy
        with it. A record where no recording holds a frame keeps every one of them, since nothing
        sounds that could tell them apart.

        Args:
            playing: The channels whose streams sound somewhere.

        Returns:
            StemsData: The record of the channels in play and the recordings behind them.
        """
        record = self.with_assignments([item for item in self.assignments if item.channel_name in playing])
        holding = record.holding_stem_ids
        if not holding:
            return record

        return record.without_entries(frozenset(record.config.entries_by_id) - holding)

    def _with_sources(self, sources: List[StemSource]) -> StemsData:
        """This record carrying ``sources`` in place of the ones it names."""
        return self._rebuilt(
            config=self.config,
            sources=sources,
            assignments=self.assignments,
        )

    def _rebuilt(
        self,
        *,
        config: StemsConfig,
        sources: Sequence[StemSource],
        assignments: Sequence[ChannelAssignment],
    ) -> StemsData:
        """A record built afresh from its parts, so its memoized views follow what it now holds.

        The scale belongs to the conversion and stays whatever the record now holds, so every
        recording that stays is read at the level the conversion read it at.
        """
        return StemsData(
            config=config,
            sources=tuple(sources),
            assignments=tuple(assignments),
            scale=self.scale,
        )
