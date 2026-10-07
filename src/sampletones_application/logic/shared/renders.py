import threading
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from sampletones_core.audio.mixing import mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators.render import render_instructions
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem


class RenderKind(StrEnum):
    CHANNEL = "channel"
    MIX = "mix"


@dataclass(frozen=True)
class RenderKey:
    """What one render was made from: the identities of the streams it sounds and the configuration it ran at."""

    kind: RenderKind
    streams: Tuple[int, ...]
    config: Config


class RenderCache:
    """The audio the documents on screen render to, kept apart from the documents themselves.

    A reconstruction is a value that the undo history holds for as long as an entry names it,
    so audio cached on it would live as long as the history does. The cache keeps renders
    instead, each made from one channel's stream at one configuration, or one mix of such
    streams. A stream an edit leaves alone is the very object the edited document holds, so its
    render serves both documents.

    A render is keyed by the identity of the streams it sounds, which a lookup reads at once,
    where a stream's value would take every instruction it carries to hash. A render goes with
    the stream it was made from, and beyond ``budget_bytes`` the renders read longest ago go
    first, so the cache keeps audio alone. The render thread reads the cache, and a stream's
    collection may drop its renders from any thread, so every change to the cache is made
    under one lock.
    """

    def __init__(self, *, budget_bytes: int) -> None:
        self._budget_bytes = budget_bytes
        self._renders: OrderedDict[RenderKey, np.ndarray] = OrderedDict()
        self._watched: Set[int] = set()
        self._held_bytes = 0
        self._lock = threading.Lock()

    @property
    def held_bytes(self) -> int:
        """How many bytes the renders the cache keeps take."""
        return self._held_bytes

    def channels(self, reconstruction: Reconstruction) -> Dict[ChannelName, np.ndarray]:
        """The audio each channel in play renders from the stream it carries."""
        return {
            stream.channel_name: self._channel(stream, reconstruction.config)
            for stream in self._sounding(reconstruction)
        }

    def mix(self, reconstruction: Reconstruction) -> np.ndarray:
        """The whole reconstruction, summed from the channels that play."""
        streams = self._sounding(reconstruction)
        key = RenderKey(RenderKind.MIX, tuple(id(stream) for stream in streams), reconstruction.config)
        cached = self._read(key)
        if cached is not None:
            return cached

        mixed = mix([self._channel(stream, reconstruction.config) for stream in streams])
        self._keep(key, mixed, streams)
        return mixed

    @staticmethod
    def _sounding(reconstruction: Reconstruction) -> List[InstructionsItem]:
        """The streams that describe a frame, in channel order, the channels a render sounds."""
        return [stream for stream in reconstruction.instructions_data if stream.instructions]

    def _channel(self, stream: InstructionsItem, config: Config) -> np.ndarray:
        key = RenderKey(RenderKind.CHANNEL, (id(stream),), config)
        cached = self._read(key)
        if cached is not None:
            return cached

        rendered = render_instructions(
            [data.instruction for data in stream.instructions],
            stream.channel_name,
            config,
        )
        self._keep(key, rendered, [stream])
        return rendered

    def _read(self, key: RenderKey) -> Optional[np.ndarray]:
        with self._lock:
            rendered = self._renders.get(key)
            if rendered is not None:
                self._renders.move_to_end(key)

            return rendered

    def _keep(
        self,
        key: RenderKey,
        rendered: np.ndarray,
        streams: List[InstructionsItem],
    ) -> None:
        with self._lock:
            if key in self._renders:
                return

            self._renders[key] = rendered
            self._held_bytes += rendered.nbytes
            for stream in streams:
                if id(stream) not in self._watched:
                    self._watched.add(id(stream))
                    weakref.finalize(stream, self._forget, id(stream))

            while self._held_bytes > self._budget_bytes and len(self._renders) > 1:
                _, evicted = self._renders.popitem(last=False)
                self._held_bytes -= evicted.nbytes

    def _forget(self, stream_id: int) -> None:
        """Drops every render a collected stream sounds in, before its identity can name another."""
        with self._lock:
            self._watched.discard(stream_id)
            for key in [key for key in self._renders if stream_id in key.streams]:
                self._held_bytes -= self._renders.pop(key).nbytes
