from typing import Type, TypeVar, Union

from .implementation.lfsr import LFSRTimer
from .implementation.phase import PhaseTimer
from .timer import Timer

TimerT = TypeVar("TimerT", bound=Timer)
TimerUnion = Union[PhaseTimer, LFSRTimer]
TimerTypeUnion = Union[Type[PhaseTimer], Type[LFSRTimer]]
