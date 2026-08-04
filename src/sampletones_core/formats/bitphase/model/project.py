from typing import Dict, Tuple

from pydantic import BaseModel, Field

from sampletones_core.formats.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.formats.bitphase.model.instrument import BitphaseInstrument
from sampletones_core.formats.bitphase.model.song import BitphaseSong
from sampletones_core.formats.bitphase.model.table import BitphaseTable
from sampletones_core.formats.bitphase.specification.patterns import FIRST_PATTERN_ID


class BitphaseProject(BaseModel):
    """Everything one Bitphase document holds.

    Instruments and tables are owned by the project rather than by a song, so every
    song addresses the same instrument list. ``pattern_order`` names the pattern each
    order position plays, and ``loop_point_id`` is the position playback returns to.
    """

    model_config = BITPHASE_MODEL_CONFIG

    name: str = Field(
        ...,
        description="Title shown for the document.",
    )
    author: str = Field(
        ...,
        description="Author credited for the document.",
    )
    songs: Tuple[BitphaseSong, ...] = Field(
        ...,
        description="Every song the document holds.",
    )
    loop_point_id: int = Field(
        default=FIRST_PATTERN_ID,
        ge=0,
        description="Order position playback returns to at the end.",
    )
    pattern_order: Tuple[int, ...] = Field(
        ...,
        description="Pattern id played at each order position.",
    )
    tables: Tuple[BitphaseTable, ...] = Field(
        ...,
        description="Every semitone contour the patterns attach.",
    )
    pattern_order_colors: Dict[int, str] = Field(
        default_factory=dict,
        description="Highlight colour per order position.",
    )
    instruments: Tuple[BitphaseInstrument, ...] = Field(
        ...,
        description="Every instrument the patterns trigger.",
    )
