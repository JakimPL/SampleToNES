from __future__ import annotations

from typing import Final, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.specification.screen import COLORS_PER_PALETTE, TILE_SIDE

INK: Final[str] = "#"
PAPER: Final[str] = "."
LITERAL_COLORS: Final[str] = "".join(str(color) for color in range(COLORS_PER_PALETTE))
SYMBOLS: Final[str] = INK + PAPER + LITERAL_COLORS

Pixels = Tuple[Tuple[int, ...], ...]


class Drawing(BaseModel):
    """One tile drawn as eight rows of eight symbols.

    ``#`` takes the ink a tile group states and ``.`` its paper, so one drawing serves every group
    that recolors it. A digit names a palette entry outright, for a tile whose colors are part of
    the picture. A configuration file states a drawing as one block of text, a row per line.

    Attributes:
        rows: The eight rows, top to bottom, each eight symbols wide.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rows: Tuple[str, ...]

    @model_validator(mode="before")
    @classmethod
    def _read_the_block_a_file_states(cls, value: object) -> object:
        if isinstance(value, str):
            return {"rows": tuple(value.split())}

        return value

    @model_validator(mode="after")
    def _validate_the_tile_is_square(self) -> Drawing:
        if len(self.rows) != TILE_SIDE or any(len(row) != TILE_SIDE for row in self.rows):
            raise ValueError(f"a drawing holds {TILE_SIDE} rows of {TILE_SIDE} symbols, got {list(self.rows)}")

        return self

    @model_validator(mode="after")
    def _validate_every_symbol_is_known(self) -> Drawing:
        unknown = sorted({symbol for row in self.rows for symbol in row} - set(SYMBOLS))
        if unknown:
            raise ValueError(f"a drawing is spelled in {SYMBOLS!r}, got {unknown}")

        return self

    def pixels(self, *, ink: int, paper: int) -> Pixels:
        """The palette entry every pixel takes once the drawing is colored.

        Args:
            ink: The entry ``#`` takes.
            paper: The entry ``.`` takes.

        Returns:
            Pixels: Eight rows of eight entries.
        """
        colors = {INK: ink, PAPER: paper, **{symbol: int(symbol) for symbol in LITERAL_COLORS}}
        return tuple(tuple(colors[symbol] for symbol in row) for row in self.rows)
