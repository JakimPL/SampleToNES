import threading
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.renders import sounding_streams
from sampletones_core.reconstructions.reconstruction.stems.hearing import HeardRenders, Hearing


class RenderKind(StrEnum):
    CHANNEL = "channel"
    MIX = "mix"


@dataclass(frozen=True)
class RenderPart:
    """One channel as a render sounds it: its stream, and the owners heard where the reader leaves one out.

    Attributes:
        stream: The identity of the stream the channel plays.
        assignment: The identity of the record naming the owner of each frame, where an owner is
            left out.
        heard: The owners heard, where an owner is left out; ``None`` where the channel is heard whole.
    """

    stream: int
    assignment: Optional[int]
    heard: Optional[FrozenSet[int]]


@dataclass(frozen=True)
class RenderKey:
    """What one render was made from: the parts it sounds and the configuration it ran at."""

    kind: RenderKind
    parts: Tuple[RenderPart, ...]
    config: Config

    @property
    def identities(self) -> FrozenSet[int]:
        """The identities of every object the render was made from."""
        named = {part.stream for part in self.parts}
        named.update(part.assignment for part in self.parts if part.assignment is not None)
        return frozenset(named)


@dataclass(frozen=True)
class _Part:
    """A part beside the objects it names, which the cache watches."""

    part: RenderPart
    watched: Tuple[object, ...]


class RenderCache:
    """The audio the documents on screen render to, kept apart from the documents themselves.

    A reconstruction is a value that the undo history holds for as long as an entry names it,
    so audio cached on it would live as long as the history does. The cache keeps renders
    instead, each made from one channel's stream at one configuration, or one mix of such
    streams as a reader hears them. A stream an edit leaves alone is the very object the edited
    document holds, so its render serves both documents, and so is the record naming who holds
    each of its frames.

    A render is keyed by the identity of the parts it sounds, which a lookup reads at once, where
    a stream's value would take every instruction it carries to hash. A mix as a reader hears it
    names, for each channel the reader leaves an owner out on, the record and the owners heard, so
    two hearings leaving nothing out read one mix. A render goes with the objects it was made
    from, and beyond ``budget_bytes`` the renders read longest ago go first, so the cache keeps
    audio alone. The cache renders nothing: every render it keeps is a worker's result, adopted at
    its landing on the render thread, and a reading the cache cannot answer is what a worker is
    asked for, so the render thread computes no sample. The render thread reads the cache and
    keeps what it adopts, and an object's collection may drop its renders from any thread, so
    every change to the cache is made under one lock. The lock lets its holder in again, since a
    stream let go of while a keep runs on the same thread is forgotten from inside that keep. A
    kept render is read-only, so the readers it is shared with copy what they change.
    """

    def __init__(self, *, budget_bytes: int) -> None:
        self._budget_bytes = budget_bytes
        self._renders: OrderedDict[RenderKey, np.ndarray] = OrderedDict()
        self._watched: set[int] = set()
        self._held_bytes = 0
        self._lock = threading.RLock()

    @property
    def held_bytes(self) -> int:
        """How many bytes the renders the cache keeps take."""
        return self._held_bytes

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

    def reading(
        self,
        reconstruction: Reconstruction,
        hearing: Hearing,
    ) -> Optional[HeardRenders]:
        """What the cache holds of ``hearing``'s reading of ``reconstruction``, which a lookup answers at once.

        Returns:
            Optional[HeardRenders]: The heard mix and what plays, or ``None`` where either is
            missing, which is what a worker is then asked to render.
        """
        parts = self._heard_parts(reconstruction, hearing)
        mixed = self._read(self._mix_key(list(parts.values()), reconstruction.config))
        playing = self._read(self._mix_key(self._playing_parts(parts, hearing), reconstruction.config))
        if mixed is None or playing is None:
            return None

        return HeardRenders(mix=mixed, playing=playing)

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

        parts = [self._plain_part(stream) for stream in streams]
        self._keep(self._mix_key(parts, reconstruction.config), mixed, streams)

    def adopt_heard(
        self,
        reconstruction: Reconstruction,
        hearing: Hearing,
        heard: HeardRenders,
    ) -> None:
        """Keeps what a hearing of the document sounds, rendered elsewhere, under the parts it was heard as.

        Args:
            reconstruction: The document the renders sound.
            hearing: What the reader heard of it when the renders were made.
            heard: The heard mix and what plays.
        """
        parts = self._heard_parts(reconstruction, hearing)
        self._keep_mix(list(parts.values()), reconstruction.config, heard.mix)
        self._keep_mix(self._playing_parts(parts, hearing), reconstruction.config, heard.playing)

    def _keep_mix(self, parts: List[_Part], config: Config, mixed: np.ndarray) -> None:
        self._keep(
            self._mix_key(parts, config),
            mixed,
            [watched for part in parts for watched in part.watched],
        )

    @staticmethod
    def _plain_part(stream: InstructionsItem) -> _Part:
        return _Part(part=RenderPart(stream=id(stream), assignment=None, heard=None), watched=(stream,))

    @staticmethod
    def _heard_parts(reconstruction: Reconstruction, hearing: Hearing) -> Dict[ChannelName, _Part]:
        """Each channel in play as ``hearing`` sounds it, in channel order."""
        stems_data = reconstruction.stems_data
        parts: Dict[ChannelName, _Part] = {}
        for stream in sounding_streams(reconstruction):
            heard = hearing.filter_for(stream.channel_name, stems_data)
            if heard is None:
                parts[stream.channel_name] = RenderCache._plain_part(stream)
                continue

            record = stems_data.assignment_records[stream.channel_name]
            parts[stream.channel_name] = _Part(
                part=RenderPart(stream=id(stream), assignment=id(record), heard=heard),
                watched=(stream, record),
            )

        return parts

    @staticmethod
    def _playing_parts(parts: Mapping[ChannelName, _Part], hearing: Hearing) -> List[_Part]:
        return [part for channel_name, part in parts.items() if channel_name in hearing.channels_on]

    @staticmethod
    def _channel_key(stream: InstructionsItem, config: Config) -> RenderKey:
        return RenderKey(RenderKind.CHANNEL, (RenderPart(stream=id(stream), assignment=None, heard=None),), config)

    @staticmethod
    def _mix_key(parts: Sequence[_Part], config: Config) -> RenderKey:
        return RenderKey(RenderKind.MIX, tuple(part.part for part in parts), config)

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
        watched: Sequence[object],
    ) -> None:
        with self._lock:
            if key in self._renders:
                return

            rendered.setflags(write=False)
            self._renders[key] = rendered
            self._held_bytes += rendered.nbytes
            for named in watched:
                if id(named) not in self._watched:
                    self._watched.add(id(named))
                    weakref.finalize(named, self._forget, id(named))

            while self._held_bytes > self._budget_bytes and len(self._renders) > 1:
                _, evicted = self._renders.popitem(last=False)
                self._held_bytes -= evicted.nbytes

    def _forget(self, identity: int) -> None:
        """Drops every render a collected stream or record sounds in, before its identity can name another."""
        with self._lock:
            self._watched.discard(identity)
            for key in [key for key in self._renders if identity in key.identities]:
                self._held_bytes -= self._renders.pop(key).nbytes
