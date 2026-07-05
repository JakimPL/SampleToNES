from __future__ import annotations

from typing import Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_shared.constants.project import (
    MAX_ROWS_PER_PATTERN,
    MIN_ROWS_PER_PATTERN,
)


class Song(BaseModel):
    """The pattern arrangement across the four NES channels.

    ``order`` is the single source of truth for the arrangement: each entry is one
    frame (order position) mapping every channel to the pattern index it plays, or
    ``None`` for a silent slot. All channels therefore share the same order length
    automatically.

    ``rows_per_pattern`` is the invariant row count for every pattern in this song.
    Changing it via :meth:`resize_patterns` resizes all existing patterns in place.
    """

    model_config = ConfigDict(validate_assignment=True)

    rows_per_pattern: int = Field(
        ...,
        ge=MIN_ROWS_PER_PATTERN,
        le=MAX_ROWS_PER_PATTERN,
        description="Row count enforced for every pattern.",
    )
    order: List[Dict[GeneratorName, Optional[int]]] = Field(
        ..., description="Arrangement: one frame per position, mapping each channel to a pattern index."
    )
    channels: Dict[GeneratorName, Channel] = Field(..., description="Pattern pool per NES channel.")

    @classmethod
    def empty(cls, rows_per_pattern: int) -> Song:
        channels = {generator: Channel.empty(generator, rows_per_pattern) for generator in GeneratorName.items()}
        first_frame: Dict[GeneratorName, Optional[int]] = {generator: 0 for generator in GeneratorName.items()}
        return cls(rows_per_pattern=rows_per_pattern, order=[first_frame], channels=channels)

    def __getitem__(self, generator: GeneratorName) -> Channel:
        return self.channels[generator]

    def pattern(self, generator: GeneratorName, index: int) -> Optional[Pattern]:
        return self.channels[generator].pattern(index)

    def order_length(self) -> int:
        return len(self.order)

    def ordered_patterns(self, generator: GeneratorName) -> List[Optional[Pattern]]:
        channel = self.channels[generator]
        return [
            channel.patterns.get(index) if index is not None else None
            for index in (frame.get(generator) for frame in self.order)
        ]

    def _empty_frame(self) -> Dict[GeneratorName, Optional[int]]:
        return {generator: None for generator in GeneratorName.items()}

    def append_frame(self) -> None:
        self.order.append(self._empty_frame())

    def insert_frame(self, position: int) -> None:
        self.order.insert(position, self._empty_frame())

    def set_order_entry(self, position: int, generator: GeneratorName, index: Optional[int]) -> None:
        self.order[position][generator] = index

    def remove_frame(self, position: int) -> None:
        del self.order[position]

    def move_frame(self, from_position: int, to_position: int) -> None:
        frame = self.order.pop(from_position)
        self.order.insert(to_position, frame)

    def add_pattern(self, generator: GeneratorName) -> int:
        """Adds an empty pattern to ``generator`` at a free index and returns it.

        The index clears both the channel's pool and every index its order slots
        already reference, so it never aliases a slot whose pattern is unmaterialised.
        """
        return self.channels[generator].add_pattern(
            self.rows_per_pattern,
            reserved_indices=self._referenced_indices(generator),
        )

    def duplicate_pattern(self, generator: GeneratorName, index: int) -> int:
        """Clones ``generator``'s pattern at ``index`` into a free index and returns it.

        The clone index clears the channel's pool and every order-referenced index, so
        the copy stays independent of any slot the order already plays.
        """
        return self.channels[generator].duplicate_pattern(
            index,
            reserved_indices=self._referenced_indices(generator),
        )

    def duplicate_frame(self, position: int) -> None:
        """Inserts an independent copy of the frame directly after ``position``.

        Each channel's referenced pattern is cloned into a fresh index within that
        channel, so the new frame plays its own patterns; editing either frame leaves
        the other unchanged. Silent slots stay silent.
        """
        source_frame = self.order[position]
        duplicate: Dict[GeneratorName, Optional[int]] = {}
        for generator in GeneratorName.items():
            index = source_frame.get(generator)
            if index is None:
                duplicate[generator] = None
                continue

            self.channels[generator].ensure_pattern(index, self.rows_per_pattern)
            duplicate[generator] = self.duplicate_pattern(generator, index)

        self.order.insert(position + 1, duplicate)

    def _referenced_indices(self, generator: GeneratorName) -> Set[int]:
        return {index for frame in self.order if (index := frame.get(generator)) is not None}

    def clear_frame(self, position: int) -> None:
        self.order[position] = self._empty_frame()

    def remove_pattern(self, generator: GeneratorName, index: int) -> None:
        """Removes a pattern from the pool and clears all order references to it."""
        self.channels[generator].remove_pattern(index)
        for frame in self.order:
            if frame.get(generator) == index:
                frame[generator] = None

    def references_sample(self, sample_id: str) -> bool:
        """Whether any row in any pattern of any channel still points at the sample."""
        return any(
            row.references_sample(sample_id)
            for channel in self.channels.values()
            for pattern in channel.patterns.values()
            for row in pattern.rows
        )

    def clear_sample_references(self, sample_id: str) -> None:
        """Clears the note-column command of every row that points at a removed sample."""
        for channel in self.channels.values():
            for pattern in channel.patterns.values():
                pattern.rows = [
                    row.model_copy(update={"command": None}) if row.references_sample(sample_id) else row
                    for row in pattern.rows
                ]

    def resize_patterns(self, rows_per_pattern: int) -> None:
        """Updates the row count for every pattern in the song.

        Existing patterns longer than the new count are truncated; shorter ones are
        extended with empty rows. The change is applied uniformly so the invariant
        holds after the call.
        """
        self.rows_per_pattern = rows_per_pattern
        empty_row = Row()
        for channel in self.channels.values():
            for pattern in channel.patterns.values():
                current = len(pattern.rows)
                if current > rows_per_pattern:
                    pattern.rows = pattern.rows[:rows_per_pattern]
                elif current < rows_per_pattern:
                    pattern.rows.extend([empty_row] * (rows_per_pattern - current))

    def __repr__(self) -> str:
        return f"Song(order_length={len(self.order)}, rows_per_pattern={self.rows_per_pattern})"
