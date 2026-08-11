from typing import Any, Protocol

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName


class ChannelGeneratorProtocol(Protocol):
    """Minimal generator interface required by the synthesis engine.

    Each NES channel's generator synthesises one tick of audio from an
    instruction. The concrete type is generic (``Generator[InstructionT,
    TimerT]``); this protocol captures only the surface the synthesiser
    actually uses so that invariant generic instantiations (e.g.
    ``PulseGenerator``) are accepted while keeping their precise generic types.

    The instruction parameter is typed ``Any`` because the generator-to-instruction
    pairing is a runtime invariant maintained by ``GENERATOR_CLASSES`` dispatch, which
    lies outside the static type system.

    ``frame_length`` is settable so the synthesiser can give each tick the span its clock
    states, which is what keeps a rendered tick lasting ``1 / nes_frequency`` seconds at a
    sample rate the tick divides unevenly.
    """

    frame_length: int

    def __call__(
        self,
        instruction: Any,
        /,
        initials: Any = None,
        save: bool = False,
    ) -> np.ndarray: ...

    def reset(self) -> None: ...

    def class_name(self) -> GeneratorClassName: ...
