from typing import Type, TypeVar, Union

from .lfsr import LFSRTimer
from .phase import PhaseTimer
from .timer import Timer

TimerT = TypeVar("TimerT", bound=Timer)
TimerUnion = Union[PhaseTimer, LFSRTimer]
TimerTypeUnion = Union[Type[PhaseTimer], Type[LFSRTimer]]
