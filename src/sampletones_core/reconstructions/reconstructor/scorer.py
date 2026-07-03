from dataclasses import dataclass, field

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_shared.array import CUPY_AVAILABLE, xp

from ..criterion import Criterion


@dataclass(frozen=True)
class Scorer:
    config: Config
    window: Window
    signal_length: int

    criterion: Criterion = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "criterion", Criterion(self.config, self.window, self.signal_length))

    def best(self, target: Fragment, candidates: Fragment) -> int:
        errors = None
        target_gpu = None
        try:
            target_gpu = target.to_cupy()
            errors = self.criterion(target_gpu, candidates)
            return int(xp.argmin(errors))
        finally:
            del errors, target_gpu
            if CUPY_AVAILABLE:
                xp.get_default_memory_pool().free_all_blocks()

    def costs(self, target: Fragment, candidates: Fragment) -> np.ndarray:
        errors = None
        target_gpu = None
        try:
            target_gpu = target.to_cupy()
            errors = self.criterion(target_gpu, candidates)
            return self._to_host(errors)
        finally:
            del errors, target_gpu
            if CUPY_AVAILABLE:
                xp.get_default_memory_pool().free_all_blocks()

    @staticmethod
    def top_k(costs: np.ndarray, k: int) -> np.ndarray:
        count = min(k, int(costs.shape[0]))
        partitioned = np.argpartition(costs, count - 1)[:count]
        return partitioned[np.argsort(costs[partitioned])]

    @staticmethod
    def _to_host(errors: xp.ndarray) -> np.ndarray:
        return xp.asnumpy(errors) if CUPY_AVAILABLE else np.asarray(errors)
