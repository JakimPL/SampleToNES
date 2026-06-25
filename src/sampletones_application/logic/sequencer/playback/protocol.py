from typing import Any, Protocol

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName


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
