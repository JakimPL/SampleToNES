from __future__ import annotations

from enum import IntEnum
from typing import Final, List, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_player.specification.screen import (
    BACKGROUND_TABLE,
    COLORS_PER_PALETTE,
    SPRITE_TABLE,
    TILES_PER_TABLE,
)
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.player.graphics.paths import SHEET_PATH

NO_CHARACTERS: Final[str] = ""
NO_SHAPES: Final[Tuple[str, ...]] = ()
LAST_COLOR: Final[int] = COLORS_PER_PALETTE - 1


class PatternTable(IntEnum):
    """One of the two tables of 256 tiles a cartridge holds: the screen's own, and the sprites'."""

    BACKGROUND = BACKGROUND_TABLE
    SPRITES = SPRITE_TABLE


class TileGroup(BaseModel):
    """A run of consecutive tiles drawn in one pair of colors.

    A group states where its run starts, so a tile's number follows from the group and the member's
    place in it, and stays where it is while other groups change. The characters come first, in the
    order the group spells them, and the shapes follow.

    Attributes:
        name: The name the screen layout refers to the group by.
        first: The number of the group's first tile.
        ink: The palette entry the drawn pixels take.
        paper: The palette entry the pixels around them take.
        characters: The font characters the group holds.
        shapes: The named shapes the group holds.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    first: int = Field(ge=0, lt=TILES_PER_TABLE)
    ink: int = Field(ge=0, le=LAST_COLOR)
    paper: int = Field(ge=0, le=LAST_COLOR)
    characters: str = NO_CHARACTERS
    shapes: Tuple[str, ...] = NO_SHAPES

    @model_validator(mode="after")
    def _validate_the_members_are_distinct(self) -> TileGroup:
        if len(set(self.members)) != len(self.members):
            raise ValueError(f"the tile group {self.name} names a member twice")

        return self

    @model_validator(mode="after")
    def _validate_the_group_fits_its_table(self) -> TileGroup:
        if self.first + len(self.members) > TILES_PER_TABLE:
            raise ValueError(f"the tile group {self.name} runs past the {TILES_PER_TABLE} tiles a table holds")

        return self

    @property
    def members(self) -> Tuple[str, ...]:
        """Every member, in the order the group's tiles hold them."""
        return tuple(self.characters) + self.shapes

    @property
    def tiles(self) -> range:
        """The tile numbers the group takes."""
        return range(self.first, self.first + len(self.members))

    def tile(self, member: str) -> int:
        """The number of the tile holding ``member``.

        Raises:
            KeyError: If the group holds no such member.
        """
        if member not in self.members:
            raise KeyError(f"the tile group {self.name} holds no {member!r}")

        return self.first + self.members.index(member)


class SheetGroups(BaseModel):
    """The tile groups each pattern table is laid out in.

    Attributes:
        background: The groups of the screen's own table.
        sprites: The groups of the sprites' table.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    background: Tuple[TileGroup, ...]
    sprites: Tuple[TileGroup, ...]

    @model_validator(mode="after")
    def _validate_the_groups_stand_apart(self) -> SheetGroups:
        for table in (self.background, self.sprites):
            names = [group.name for group in table]
            if len(set(names)) != len(names):
                raise ValueError("a pattern table names each of its tile groups once")

            taken: List[int] = [tile for group in table for tile in group.tiles]
            if len(set(taken)) != len(taken):
                raise ValueError("two tile groups of one pattern table take the same tile")

        return self

    @classmethod
    def load(cls) -> SheetGroups:
        """The groups the package ships."""
        return load_yaml_model(SHEET_PATH, cls)
