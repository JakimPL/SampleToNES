from __future__ import annotations

from dataclasses import dataclass
from typing import Final, List, Sequence

from sampletones_player.specification.screen import SCREEN_HEIGHT, SPRITE_COUNT

SPRITE_SIZE: Final[int] = 4
SCANLINE_DELAY: Final[int] = 1
OFF_SCREEN: Final[int] = 0xF0


@dataclass(frozen=True)
class Sprite:
    """A sprite as the console holds it, spelled out since the hardware format is the contract.

    A sprite takes four bytes of the sprite memory, in the order of the attributes below, and
    shows one scanline below the vertical position it states.

    Attributes:
        vertical: The scanline above the sprite's top row.
        tile: The tile of the sprites' pattern table the sprite draws.
        attributes: The sprite's attribute byte, whose two low bits choose its palette.
        horizontal: The sprite's leftmost pixel.
    """

    vertical: int
    tile: int
    attributes: int
    horizontal: int

    @property
    def top(self) -> int:
        """The scanline the sprite's top row is shown on."""
        return self.vertical + SCANLINE_DELAY

    @property
    def shown(self) -> bool:
        """Whether any row of the sprite lies on the screen."""
        return self.top < SCREEN_HEIGHT

    def to_bytes(self) -> bytes:
        return bytes((self.vertical, self.tile, self.attributes, self.horizontal))


HIDDEN: Final[Sprite] = Sprite(vertical=OFF_SCREEN, tile=0, attributes=0, horizontal=0)


def sprites_of(memory: bytes) -> List[Sprite]:
    """Reads a sprite memory back into its sprites, four bytes each."""
    return [Sprite(*memory[start : start + SPRITE_SIZE]) for start in range(0, len(memory), SPRITE_SIZE)]


def shown_sprites(memory: bytes) -> List[Sprite]:
    """The sprites of a sprite memory that reach the screen, in the order the memory holds them."""
    return [sprite for sprite in sprites_of(memory) if sprite.shown]


def sprite_memory(sprites: Sequence[Sprite]) -> bytes:
    """A whole sprite memory opening with ``sprites``, every sprite after them off the screen."""
    held = [*sprites, *[HIDDEN] * (SPRITE_COUNT - len(sprites))]
    return b"".join(sprite.to_bytes() for sprite in held)
