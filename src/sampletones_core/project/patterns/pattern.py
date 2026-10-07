from __future__ import annotations

from typing import Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .row import Row


class Pattern(BaseModel):
    """A reusable block of rows belonging to a single channel.

    A pattern is a value: an edit makes a new pattern holding the very rows it leaves alone, and the
    channel's pool puts it at the edited index. A pattern's identity is its integer key within the
    owning channel's pattern dictionary, so the model itself carries no id; the same key may be
    referenced from several order positions, and a pattern installed there is heard at every one.
    """

    model_config = ConfigDict(frozen=True)

    name: Optional[str] = Field(default=None, description="Optional human-readable name.")
    rows: Tuple[Row, ...] = Field(..., description="Tracker lines, in order.")

    @classmethod
    def empty(
        cls,
        length: int,
        name: Optional[str] = None,
    ) -> Pattern:
        return cls(rows=(Row(),) * length, name=name)

    @property
    def length(self) -> int:
        return len(self.rows)

    def is_empty(self) -> bool:
        return all(row.is_empty() for row in self.rows)

    def with_row(
        self,
        index: int,
        row: Row,
    ) -> Pattern:
        """The pattern holding ``row`` at ``index`` and every other row as it stands."""
        return self.with_rows({index: row})

    def with_rows(self, rows: Mapping[int, Row]) -> Pattern:
        """The pattern holding each of ``rows`` at its index and every other row as it stands."""
        updated = list(self.rows)
        for index, row in rows.items():
            updated[index] = row

        written: Pattern = self.model_copy(update={"rows": tuple(updated)})
        return written

    def resized(self, length: int) -> Pattern:
        """The pattern cut to ``length`` rows, or carried there with empty rows, the rows it keeps shared."""
        if length == len(self.rows):
            return self

        kept = self.rows[:length]
        resized: Pattern = self.model_copy(update={"rows": kept + (Row(),) * (length - len(kept))})
        return resized

    def without_voice(self, voice_id: str) -> Pattern:
        """The pattern with every note naming ``voice_id`` cleared, the very pattern where none does."""
        if not any(row.references_voice(voice_id) for row in self.rows):
            return self

        cleared = tuple(
            row.model_copy(update={"command": None}) if row.references_voice(voice_id) else row for row in self.rows
        )
        released: Pattern = self.model_copy(update={"rows": cleared})
        return released

    def __repr__(self) -> str:
        return f"Pattern(name={self.name!r}, length={self.length})"
