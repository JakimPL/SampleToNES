from dataclasses import dataclass
from typing import Iterator, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.instructions import InstructionUnion

from .profiles import FrameProfiles

NoteKey = Tuple[int, int]


@dataclass
class ChannelLine:
    """One channel's frames as the analysis hears them, each frame settled on what it plays.

    A line starts from a decode and takes each frame's new choice as a pass settles it, so a frame
    assigned later in the pass hears the choices taken before it.

    Attributes:
        keys: The note and timbre each frame sounds, ``None`` where the channel is silent. Frames in a
            row sounding one key hold one note.
        powers: Each frame's power per bin at the drive the channel is played at, one row per frame.
        instructions: What the channel plays in each frame.
        coherent: Whether a held note keeps its phase from frame to frame, as a tonal channel's does.
            The noise's frames add in power.
    """

    keys: List[Optional[NoteKey]]
    powers: np.ndarray
    instructions: List[InstructionUnion]
    coherent: bool

    def settle(self, frame: int, key: Optional[NoteKey], power: np.ndarray, instruction: InstructionUnion) -> None:
        """Settles ``frame`` on playing ``instruction``, which sounds ``key`` at ``power``."""
        self.keys[frame] = key
        self.powers[frame] = power
        self.instructions[frame] = instruction


@dataclass(frozen=True)
class Neighbor:
    """A note held by the frames beside a frame, up to it or from it on.

    Attributes:
        key: The note and timbre the frames sound.
        amplitude: What the note reaches each of the frame's bins with, in amplitude.
        share: The share of each bin's window weight the note's frames hold.
    """

    key: NoteKey
    amplitude: np.ndarray
    share: np.ndarray


@dataclass(frozen=True)
class ChannelSurroundings:
    """What one channel's other frames leave in a frame's reading, and the notes held up to the frame and from it.

    A row the frame plays on the channel adds its own share of its power. On a tonal channel, a row
    sounding the note held up to the frame or the note held from it extends that note, and the two
    add in amplitude, so a note held through the frame reaches it as a note held throughout does.

    Attributes:
        leak: The power the channel's other frames leave in the frame's bins.
        before: The note held up to the frame, or ``None``.
        after: The note held from the frame on, or ``None``.
        own: The frame's own share of each bin's window: of its weight where notes add in amplitude,
            of its squared weight where they add in power.
        coherent: Whether the channel's held notes add in amplitude.
    """

    leak: np.ndarray
    before: Optional[Neighbor]
    after: Optional[Neighbor]
    own: np.ndarray
    coherent: bool

    def heard(self, keys: Sequence[Optional[NoteKey]], powers: np.ndarray) -> np.ndarray:
        """The power each row adds to the frame's reading when the frame plays it on the channel.

        Args:
            keys: Each row's note and timbre, ``None`` for silence.
            powers: Each row's power per bin at the channel's drive, one row per key.

        Returns:
            Each row's added power, shaped as ``powers``.
        """
        if not self.coherent:
            return np.asarray(self.own * powers)

        extends_before, extends_after = self._extended(keys)
        reach = np.zeros_like(powers)
        if self.before is not None:
            reach = reach + extends_before[:, None] * self.before.amplitude
        if self.after is not None:
            reach = reach + extends_after[:, None] * self.after.amplitude
        added = np.square(self.own) * powers + 2.0 * self.own * np.sqrt(powers) * reach
        if self.before is not None and self.after is not None:
            bridged = (extends_before & extends_after)[:, None]
            added = added + bridged * 2.0 * self.before.amplitude * self.after.amplitude

        return np.asarray(added)

    def gains(self, keys: Sequence[Optional[NoteKey]]) -> np.ndarray:
        """How much of each row's power reaches the frame's reading, its note at the level of the note it extends.

        A fitted level scales a row's power, so a fit reads a row through this gain, which is exact
        where the row plays at the level of the note it extends.

        Args:
            keys: Each row's note and timbre, ``None`` for silence.

        Returns:
            Each row's gain per bin, one row per key.
        """
        rows = len(keys)
        if not self.coherent:
            return np.tile(self.own, (rows, 1))

        extends_before, extends_after = self._extended(keys)
        share = np.zeros((rows, self.own.shape[0]))
        if self.before is not None:
            share = share + extends_before[:, None] * self.before.share
        if self.after is not None:
            share = share + extends_after[:, None] * self.after.share
        gains = np.square(self.own) + 2.0 * self.own * share
        if self.before is not None and self.after is not None:
            bridged = (extends_before & extends_after)[:, None]
            gains = gains + bridged * 2.0 * self.before.share * self.after.share

        return np.asarray(gains)

    def extends(self, key: Optional[NoteKey]) -> bool:
        """Whether a row sounding ``key`` extends the note held up to the frame or from it."""
        return key is not None and any(
            neighbor is not None and neighbor.key == key for neighbor in (self.before, self.after)
        )

    def _extended(self, keys: Sequence[Optional[NoteKey]]) -> Tuple[np.ndarray, np.ndarray]:
        """Which rows extend the note held up to the frame, and which the note held from it."""
        before = np.array([self.before is not None and key == self.before.key for key in keys], dtype=bool)
        after = np.array([self.after is not None and key == self.after.key for key in keys], dtype=bool)
        return before, after


def surroundings(line: ChannelLine, frame: int, profiles: FrameProfiles) -> ChannelSurroundings:
    """What ``line``'s other frames leave in ``frame``'s reading, and the notes held up to it and from it.

    Args:
        line: The channel's decoded frames.
        frame: The frame read.
        profiles: How each bin's window weighs the frames around the one it reads.

    Returns:
        The frame's surroundings on the channel.
    """
    if not line.coherent:
        return _noise_surroundings(line, frame, profiles)

    leak = np.zeros(line.powers.shape[1])
    before: Optional[Neighbor] = None
    after: Optional[Neighbor] = None
    for key, frames in _held_notes(line.keys, frame, profiles.reach):
        shares = np.stack([profiles.amplitude_at(held - frame) for held in frames])
        amplitude = np.sum(shares * np.sqrt(line.powers[frames]), axis=0)
        leak = leak + np.square(amplitude)
        neighbor = Neighbor(key=key, amplitude=amplitude, share=np.sum(shares, axis=0))
        if frames[-1] == frame - 1:
            before = neighbor
        if frames[0] == frame + 1:
            after = neighbor

    return ChannelSurroundings(leak=leak, before=before, after=after, own=profiles.own_amplitude, coherent=True)


def _noise_surroundings(line: ChannelLine, frame: int, profiles: FrameProfiles) -> ChannelSurroundings:
    """The noise's surroundings: every other sounding frame's power, by its share of the window's squared weight."""
    leak = np.zeros(line.powers.shape[1])
    for other in _window_frames(len(line.keys), frame, profiles.reach):
        if line.keys[other] is not None:
            leak = leak + profiles.energy_at(other - frame) * line.powers[other]

    return ChannelSurroundings(leak=leak, before=None, after=None, own=profiles.own_energy, coherent=False)


def _held_notes(keys: Sequence[Optional[NoteKey]], frame: int, reach: int) -> Iterator[Tuple[NoteKey, List[int]]]:
    """The notes the frames within ``reach`` of ``frame`` hold, ``frame`` left out, each with its frames in a row."""
    held_key: Optional[NoteKey] = None
    held_frames: List[int] = []
    for other in _window_frames(len(keys), frame, reach):
        key = keys[other]
        if held_key is not None and (key != held_key or other != held_frames[-1] + 1):
            yield held_key, held_frames
            held_key, held_frames = None, []
        if key is None:
            continue
        if held_key is None:
            held_key = key
        held_frames.append(other)

    if held_key is not None:
        yield held_key, held_frames


def _window_frames(frames: int, frame: int, reach: int) -> Iterator[int]:
    """The frames within ``reach`` of ``frame``, ``frame`` left out."""
    for other in range(max(0, frame - reach), min(frames, frame + reach + 1)):
        if other != frame:
            yield other
