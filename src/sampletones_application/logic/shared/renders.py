import threading
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, List, Mapping, Optional, Set, Tuple

import numpy as np

from sampletones_core.audio.mixing import mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators.render import render_instructions
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.renders import sounding_streams


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
    first, so the cache keeps audio alone. The render thread reads the cache and keeps what it
    renders or adopts, and a stream's collection may drop its renders from any thread, so every
    change to the cache is made under one lock. The lock lets its holder in again, since a stream
    let go of while a keep runs on the same thread is forgotten from inside that keep. A kept
    render is read-only, so the readers it is shared with copy what they change.
    """

    def __init__(self, *, budget_bytes: int) -> None:
        self._budget_bytes = budget_bytes
        self._renders: OrderedDict[RenderKey, np.ndarray] = OrderedDict()
        self._watched: Set[int] = set()
        self._held_bytes = 0
        self._lock = threading.RLock()

    @property
    def held_bytes(self) -> int:
        """How many bytes the renders the cache keeps take."""
        return self._held_bytes

    def channels(self, reconstruction: Reconstruction) -> Dict[ChannelName, np.ndarray]:
        """The audio each channel in play renders from the stream it carries."""
        return {
            stream.channel_name: self._channel(stream, reconstruction.config)
            for stream in sounding_streams(reconstruction)
        }

    def mix(self, reconstruction: Reconstruction) -> np.ndarray:
        """The whole reconstruction, summed from the channels that play."""
        streams = sounding_streams(reconstruction)
        key = self._mix_key(streams, reconstruction.config)
        cached = self._read(key)
        if cached is not None:
            return cached

        mixed = mix([self._channel(stream, reconstruction.config) for stream in streams])
        self._keep(key, mixed, streams)
        return mixed

    def held(self, reconstruction: Reconstruction) -> Dict[ChannelName, np.ndarray]:
        """The renders the cache holds for the channels in play, by channel, which a lookup answers at once.

        A rebuild takes these with it, so the worker renders the channel the edit rewrote and
        carries the rest over.
        """
        held: Dict[ChannelName, np.ndarray] = {}
        for stream in sounding_streams(reconstruction):
            cached = self._read(self._channel_key(stream, reconstruction.config))
            if cached is not None:
                held[stream.channel_name] = cached

        return held

    def adopt(
        self,
        reconstruction: Reconstruction,
        channels: Mapping[ChannelName, np.ndarray],
        mixed: np.ndarray,
    ) -> None:
        """Keeps renders made elsewhere, one per channel in play and their mix, as the document's own.

        A render the cache already holds for a stream stays as it is, so a channel rendered twice
        keeps the one the screen read first.

        Args:
            reconstruction: The document the renders sound.
            channels: The audio each channel in play renders to, by channel.
            mixed: The whole document, summed from ``channels``.
        """
        streams = sounding_streams(reconstruction)
        for stream in streams:
            self._keep(self._channel_key(stream, reconstruction.config), channels[stream.channel_name], [stream])

        self._keep(self._mix_key(streams, reconstruction.config), mixed, streams)

    @staticmethod
    def _channel_key(stream: InstructionsItem, config: Config) -> RenderKey:
        return RenderKey(RenderKind.CHANNEL, (id(stream),), config)

    @staticmethod
    def _mix_key(streams: List[InstructionsItem], config: Config) -> RenderKey:
        return RenderKey(RenderKind.MIX, tuple(id(stream) for stream in streams), config)

    def _channel(self, stream: InstructionsItem, config: Config) -> np.ndarray:
        key = self._channel_key(stream, config)
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

            rendered.setflags(write=False)
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
