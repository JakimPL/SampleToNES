from __future__ import annotations

import heapq
import threading
from dataclasses import dataclass
from typing import List

import dearpygui.dearpygui as dpg

from sampletones.typehints import VoidCallback


@dataclass(frozen=True)
class FrameCallback:
    callback: VoidCallback
    frame_count: int

    def __lt__(self, other: FrameCallback) -> bool:
        return self.frame_count < other.frame_count


class FrameCallbackManager:
    instance: FrameCallbackManager

    def __init__(self) -> None:
        self._callbacks: List[FrameCallback] = []

        self._lock = threading.Lock()

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(FrameCallbackManager, cls).__new__(cls)

        return cls.instance

    @classmethod
    def set_frame_callback(
        cls,
        callback: VoidCallback,
        frame_count: int = 1,
    ) -> None:
        self = cls()
        frame_count = dpg.get_frame_count() + max(1, frame_count)
        with self._lock:
            heapq.heappush(self._callbacks, FrameCallback(callback, frame_count))

        dpg.set_frame_callback(frame_count, self.process)

    def process(self) -> None:
        current_frame = dpg.get_frame_count()

        while True:
            with self._lock:
                if not self._callbacks or self._callbacks[0].frame_count > current_frame:
                    break

                frame_callback = heapq.heappop(self._callbacks)

            frame_callback.callback()
