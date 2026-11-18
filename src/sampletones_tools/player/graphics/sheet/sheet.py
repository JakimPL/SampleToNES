from __future__ import annotations

from typing import Final, List, Mapping, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.specification.screen import TILE_SIDE, TILES_PER_TABLE
from sampletones_tools.player.graphics.sheet.drawing import Pixels
from sampletones_tools.player.graphics.sheet.font import Font
from sampletones_tools.player.graphics.sheet.groups import PatternTable, SheetGroups, TileGroup
from sampletones_tools.player.graphics.sheet.shapes import Shapes

EMPTY_TILE: Final[Pixels] = tuple(tuple(0 for _ in range(TILE_SIDE)) for _ in range(TILE_SIDE))


class TileSheet(BaseModel):
    """Every tile the cartridge holds: the drawings, and the tile numbers they are placed at.

    Attributes:
        font: The glyph each character is drawn as.
        shapes: The named drawings.
        groups: Where each table places its runs of tiles, and the colors each run is drawn in.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    font: Font
    shapes: Shapes
    groups: SheetGroups

    @model_validator(mode="after")
    def _validate_every_member_is_drawn(self) -> TileSheet:
        for group in self.groups.background + self.groups.sprites:
            undrawn = [character for character in group.characters if not self.font.draws(character)]
            undrawn += [shape for shape in group.shapes if shape not in self.shapes.shapes]
            if undrawn:
                raise ValueError(f"the tile group {group.name} names {undrawn}, which nothing draws")

        return self

    @classmethod
    def load(cls) -> TileSheet:
        """The sheet the package ships."""
        return cls(font=Font.load(), shapes=Shapes.load(), groups=SheetGroups.load())

    def table(self, table: PatternTable) -> Mapping[str, TileGroup]:
        """The groups of one pattern table, by name."""
        groups = self.groups.background if table is PatternTable.BACKGROUND else self.groups.sprites
        return {group.name: group for group in groups}

    def tile(self, table: PatternTable, group: str, member: str) -> int:
        """The number of the tile a group holds a member at.

        Args:
            table: The pattern table the group belongs to.
            group: The group's name.
            member: A character or a shape's name.

        Returns:
            int: The tile's number within its table.

        Raises:
            KeyError: If the table holds no such group, or the group no such member.
        """
        return self.table(table)[group].tile(member)

    def drawn(self, table: PatternTable) -> Tuple[Pixels, ...]:
        """Every tile of one pattern table as colored pixels, a tile no group takes left empty.

        Args:
            table: The pattern table to draw.

        Returns:
            Tuple[Pixels, ...]: The table's 256 tiles, in tile order.
        """
        tiles: List[Pixels] = [EMPTY_TILE] * TILES_PER_TABLE
        for group in self.table(table).values():
            for character in group.characters:
                tiles[group.tile(character)] = self.font.glyph(character).pixels(ink=group.ink, paper=group.paper)

            for shape in group.shapes:
                tiles[group.tile(shape)] = self.shapes.shapes[shape].pixels(ink=group.ink, paper=group.paper)

        return tuple(tiles)
