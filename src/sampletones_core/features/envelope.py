from typing import Generic, Optional, Tuple, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

ItemT = TypeVar("ItemT")


class Envelope(BaseModel, Generic[ItemT]):
    """One dimension read per tick: the values it writes, and the value they repeat from.

    Each dimension advances on a counter of its own, which is what lets an attack on the volume
    sit beside a duty cycle that circles every other tick. A dimension reaching its last item
    holds that value for as long as the note sounds, so a trailing zero on the volume is what
    releases a note; one stating a loop point circles from that item instead.

    The point travels with the items it indexes, so every operation that reshapes a dimension
    reshapes both together and one can never be read against a stale other.

    Attributes:
        items: The value this dimension writes per tick, empty where the channel governs it.
        loop_point: The item index the dimension repeats from, or ``None`` where it holds its last.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: Tuple[ItemT, ...] = ()
    loop_point: Optional[int] = Field(
        default=None,
        ge=0,
        description="Item index the dimension repeats from, or None where it holds its last item.",
    )

    @model_validator(mode="after")
    def _check_loop_point(self) -> "Envelope[ItemT]":
        if self.loop_point is not None and self.loop_point >= len(self.items):
            raise ValueError(f"loop point {self.loop_point} stands past the {len(self.items)} items written")

        return self

    @property
    def loops(self) -> bool:
        """Whether the dimension circles from a point rather than holding its last item."""
        return self.loop_point is not None

    @property
    def written(self) -> bool:
        """Whether the instrument writes this dimension, which takes it out of the channel's own."""
        return bool(self.items)

    def at(self, tick: int) -> Optional[ItemT]:
        """The value this dimension holds at a tick of a sounding note.

        Args:
            tick: Ticks since the note started.

        Returns:
            Optional[ItemT]: The value written, or ``None`` where the channel governs this dimension.
        """
        if not self.items:
            return None

        if tick < len(self.items):
            return self.items[tick]

        if self.loop_point is None:
            return self.items[-1]

        cycle = len(self.items) - self.loop_point
        return self.items[self.loop_point + (tick - self.loop_point) % cycle]

    def limited(self, limit: int) -> "Envelope[ItemT]":
        """This dimension's opening items, at most ``limit`` of them.

        A point standing past what survives moves to the last item kept, which is the value the
        dimension would hold there anyway. Whoever states the limit is where it comes from, so a
        dimension carries whatever length it was written at until a target asks for less.

        Args:
            limit: The most items to keep.

        Returns:
            Envelope[ItemT]: The dimension within that limit, with its point kept inside it.
        """
        if len(self.items) <= limit:
            return self

        return self._holding(self.items[:limit])

    def resized(self, length: int) -> "Envelope[ItemT]":
        """This dimension brought to a length, holding its final value where it falls short.

        A format storing one row per tick reads every dimension out of the same row, so a
        dimension shorter than its siblings holds the value it ended on for the rest of them.

        Args:
            length: The item count to reach.

        Returns:
            Envelope[ItemT]: The dimension at that length, with its point kept inside it.
        """
        if not self.items or len(self.items) == length:
            return self

        return self._holding(self.items[:length] + self.items[-1:] * (length - len(self.items)))

    def with_items(self, items: Tuple[ItemT, ...]) -> "Envelope[ItemT]":
        """This dimension carrying different values, repeating from a point inside them.

        A reader redrawing a dimension states the values alone, so the point it already repeats
        from survives the edit and moves only far enough to stay inside what is written.

        Args:
            items: The values the dimension now writes.

        Returns:
            Envelope[ItemT]: The dimension carrying ``items``.
        """
        return self._holding(items)

    def _holding(self, items: Tuple[ItemT, ...]) -> "Envelope[ItemT]":
        """This dimension carrying ``items``, with the loop point held inside them."""
        loop_point = min(self.loop_point, len(items) - 1) if self.loop_point is not None and items else None
        return type(self)(items=items, loop_point=loop_point)
