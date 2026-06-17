from typing import Any, FrozenSet, Protocol, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName, GeneratorName
from sampletones_core.project.song_position import SongPosition


class RowSynthesizerProtocol(Protocol):
    """Streaming synthesis kernel for one-row-at-a-time playback.

    Each call to ``render_row`` produces one row's worth of audio (ticks_per_row
    × frame_length samples), advances the internal position cursor, and returns
    a snapshot of the cursor position from before the advance so callers can
    post accurate position events.
    """

    @property
    def order_position(self) -> int: ...

    @property
    def row_index(self) -> int: ...

    @property
    def is_finished(self) -> bool: ...

    def set_position(self, order_position: int, row_index: int) -> None: ...

    def set_channel_mask(self, active_channels: FrozenSet[GeneratorName]) -> None: ...

    def render_row(self) -> Tuple[np.ndarray, SongPosition]: ...

    def reset(self) -> None: ...


class ChannelGeneratorProtocol(Protocol):
    """Minimal generator interface required by the synthesis engine.

    Each NES channel's generator synthesises one tick of audio from an
    instruction. The concrete type is generic (``Generator[InstructionT,
    TimerT]``); this protocol captures only the surface the synthesiser
    actually uses so that invariant generic instantiations (e.g.
    ``PulseGenerator``) are accepted without widening to ``Any``.

    The instruction parameter is typed ``Any`` because the static type system
    cannot express the runtime invariant that each generator always receives its
    matching instruction subtype — that pairing is maintained by
    ``GENERATOR_CLASSES`` dispatch.
    """

    def __call__(self, instruction: Any, /, initials: Any = None, save: bool = False) -> np.ndarray: ...

    def reset(self) -> None: ...

    def class_name(self) -> GeneratorClassName: ...
