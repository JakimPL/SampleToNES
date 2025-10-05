from typing import Any, Optional, Tuple, Union

import numpy as np


class Timer:
    def __call__(self, length: int, direction: bool, **kwargs) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def initials(self) -> Tuple[Any, ...]:
        raise NotImplementedError("Subclasses must implement this method")

    def prepare_frame(self, length: Union[int, np.ndarray]) -> np.ndarray:
        if isinstance(length, int):
            frame = np.zeros(length, dtype=np.float32)
        elif not isinstance(length, np.ndarray):
            raise TypeError("'length' must be an int or a numpy array")

        return frame

    def reset(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def validate(self, *args, **kwargs) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def get(self) -> Tuple[Any, ...]:
        raise NotImplementedError("Subclasses must implement this method")

    def set(self, value: Optional[Tuple[Any, ...]]) -> None:
        raise NotImplementedError("Subclasses must implement this method")
