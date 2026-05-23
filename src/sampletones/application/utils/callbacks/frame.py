from __future__ import annotations

import heapq
import threading
from dataclasses import dataclass
from typing import List

import dearpygui.dearpygui as dpg

from sampletones.meta import NonInstantiableMeta
from sampletones.types.callback import VoidCallback


@dataclass(frozen=True)
class FrameCallback:
    callback: VoidCallback
    frame_count: int

    def __lt__(self, other: FrameCallback) -> bool:
        return self.frame_count < other.frame_count


class FrameCallbackManager(metaclass=NonInstantiableMeta):
    _callbacks: List[FrameCallback] = []
    _lock = threading.Lock()

    @classmethod
    def set_frame_callback(
        cls,
        callback: VoidCallback,
        frame_count: int = 1,
    ) -> None:
        frame_count = dpg.get_frame_count() + max(1, frame_count)
        frame_callback = FrameCallback(callback, frame_count)
        with cls._lock:
            heapq.heappush(cls._callbacks, frame_callback)

        dpg.set_frame_callback(frame_count, cls.process)

    @classmethod
    def process(cls) -> None:
        current_frame = dpg.get_frame_count()

        while True:
            with cls._lock:
                if not cls._callbacks or cls._callbacks[0].frame_count > current_frame:
                    break

                frame_callback = heapq.heappop(cls._callbacks)

            frame_callback.callback()
