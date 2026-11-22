from dataclasses import dataclass
from itertools import groupby
from typing import List, Optional, Protocol, Self, Sequence, Tuple

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
        keys: The note and timbre each frame sounds, ``None`` where the channel is silent.
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

    def key_at(self, frame: int) -> Optional[NoteKey]:
        """The note and timbre ``frame`` sounds, ``None`` where the channel is silent."""
        return self.keys[frame]

    def held_notes(self, frames: range) -> List[Tuple[NoteKey, range]]:
        """The notes the line holds over ``frames``: each note with the consecutive frames sounding it.

        Consecutive frames sounding one key are one note held, so grouping the consecutive ``frames``
        by the key each sounds yields the notes, and the silent groups fall away.
        """
        held: List[Tuple[NoteKey, range]] = []
        for key, grouped in groupby(frames, key=self.key_at):
            if key is not None:
                stretch = list(grouped)
                held.append((key, range(stretch[0], stretch[-1] + 1)))

        return held


@dataclass(frozen=True)
class HeldNote:
    """A note a tonal channel holds over consecutive frames beside a frame, as that frame's window reads it.

    A tonal channel keeps its phase while it holds a note, so a bin's window adds the note's frames
    in amplitude: each frame reaches the bin by its share of the window's weight times its amplitude.
    The note then leaves the square of that sum in the frame's reading.

    Attributes:
        key: The note and timbre held, ``None`` for the silence beside a frame where no note is held.
        frames: The frames holding the note.
        amplitude: What the held frames reach each of the frame's bins with, in amplitude.
        share: The held frames' share of each bin's window weight.
    """

    key: Optional[NoteKey]
    frames: range
    amplitude: np.ndarray
    share: np.ndarray

    @classmethod
    def read(cls, line: ChannelLine, key: NoteKey, frames: range, frame: int, profiles: FrameProfiles) -> Self:
        """The note ``line`` holds over ``frames``, as the window of ``frame`` reads it."""
        shares = np.stack([profiles.amplitude_at(held - frame) for held in frames])
        amplitudes = np.sqrt(line.powers[list(frames)])
        return cls(key=key, frames=frames, amplitude=np.sum(shares * amplitudes, axis=0), share=np.sum(shares, axis=0))

    @classmethod
    def silence(cls, bins: int) -> Self:
        """No note held: what a silent frame beside a frame leaves for a row to join."""
        return cls(key=None, frames=range(0), amplitude=np.zeros(bins), share=np.zeros(bins))

    @property
    def power(self) -> np.ndarray:
        """The power the note leaves in the frame's reading."""
        return np.asarray(np.square(self.amplitude))

    def ends_at(self, frame: int) -> bool:
        """Whether the note is held up to ``frame``, its last frame."""
        return bool(self.frames) and self.frames[-1] == frame

    def starts_at(self, frame: int) -> bool:
        """Whether the note is held from ``frame``, its first frame."""
        return bool(self.frames) and self.frames[0] == frame

    def joined_by(self, keys: Sequence[Optional[NoteKey]]) -> np.ndarray:
        """Which rows sound this note and so join it, as a column of ones and zeros, one row per key."""
        return np.array([[float(key is not None and key == self.key)] for key in keys])


class ChannelSurroundings(Protocol):
    """What one channel's other frames leave in a frame's reading, and what a row the frame plays adds to it.

    The frame being decided reads its neighbors through its analysis window. What they play stays
    fixed while the frame is decided, so it is the frame's leak, and each row the frame may play on
    the channel adds to the reading on top of it.
    """

    @property
    def leak(self) -> np.ndarray:
        """The power the channel's other frames leave in the frame's bins."""

    def heard(self, keys: Sequence[Optional[NoteKey]], powers: np.ndarray) -> np.ndarray:
        """The power each row adds to the frame's reading on top of the leak.

        Args:
            keys: Each row's note and timbre, ``None`` for silence.
            powers: Each row's power per bin at the channel's drive, one row per key.

        Returns:
            Each row's added power, shaped as ``powers``.
        """

    def gains(self, keys: Sequence[Optional[NoteKey]]) -> np.ndarray:
        """How much of each row's power reaches the frame's reading, where the row plays at its neighbors' level.

        A fitted level scales a row's power, so a fit reads a row through this gain. It is exact where
        the row plays at the level of the note it joins.

        Args:
            keys: Each row's note and timbre, ``None`` for silence.

        Returns:
            Each row's gain per bin, one row per key.
        """

    def extends(self, key: Optional[NoteKey]) -> bool:
        """Whether a row sounding ``key`` joins a note held beside the frame."""


@dataclass(frozen=True)
class TonalSurroundings:
    """A tonal channel around a frame being decided: the notes held beside the frame and what they leave in it.

    The frame is the one being decided, so its window is read as two sides, the frames before it
    and the frames after it. A note held through the frame therefore reads as two notes, one held up
    to the frame and one held from it.

    A row the frame plays either sounds a note of its own or joins the note held on one side, or on
    both. Joined notes are one held note, whose frames add in amplitude, so a row joining notes of
    amplitudes ``before`` and ``after`` adds ``(before + row + after)²`` less ``before²`` and ``after²``,
    which the leak already holds. A row joining the notes on both sides restores the note held
    throughout, which reaches the frame whole, as a note heard alone does.

    Attributes:
        leak: The power the notes held on both sides of the frame leave in its bins.
        before: The note held up to the frame, the silence where the frame before is silent.
        after: The note held from the frame after on, the silence where that frame is silent.
        own: The frame's own share of each bin's window weight.
    """

    leak: np.ndarray
    before: HeldNote
    after: HeldNote
    own: np.ndarray

    @classmethod
    def around(cls, line: ChannelLine, frame: int, profiles: FrameProfiles) -> Self:
        """The surroundings of ``frame`` on the tonal channel ``line``."""
        earlier, later = _window_sides(len(line.keys), frame, profiles.reach)
        notes_before = [HeldNote.read(line, key, held, frame, profiles) for key, held in line.held_notes(earlier)]
        notes_after = [HeldNote.read(line, key, held, frame, profiles) for key, held in line.held_notes(later)]
        silence = HeldNote.silence(profiles.own_amplitude.shape[0])
        return cls(
            leak=sum((note.power for note in [*notes_before, *notes_after]), np.zeros_like(silence.amplitude)),
            before=notes_before[-1] if notes_before and notes_before[-1].ends_at(frame - 1) else silence,
            after=notes_after[0] if notes_after and notes_after[0].starts_at(frame + 1) else silence,
            own=profiles.own_amplitude,
        )

    def heard(self, keys: Sequence[Optional[NoteKey]], powers: np.ndarray) -> np.ndarray:
        return _joined_power(
            self.own * np.sqrt(powers),
            self.before.joined_by(keys) * self.before.amplitude,
            self.after.joined_by(keys) * self.after.amplitude,
        )

    def gains(self, keys: Sequence[Optional[NoteKey]]) -> np.ndarray:
        return _joined_power(
            np.tile(self.own, (len(keys), 1)),
            self.before.joined_by(keys) * self.before.share,
            self.after.joined_by(keys) * self.after.share,
        )

    def extends(self, key: Optional[NoteKey]) -> bool:
        return key is not None and key in (self.before.key, self.after.key)


@dataclass(frozen=True)
class NoiseSurroundings:
    """The noise around a frame being decided: what its other sounding frames leave in the frame's reading.

    The noise's frames play different stretches of a pseudo-random sequence and share no phase, so
    they add in power: each sounding frame reaches a bin by its share of the window's squared weight
    times its power. A row the frame plays adds its own share likewise and joins no note.

    Attributes:
        leak: The power the noise's frames on both sides of the frame leave in its bins.
        own: The frame's own share of each bin's squared window weight.
    """

    leak: np.ndarray
    own: np.ndarray

    @classmethod
    def around(cls, line: ChannelLine, frame: int, profiles: FrameProfiles) -> Self:
        """The surroundings of ``frame`` on the noise channel ``line``."""
        earlier, later = _window_sides(len(line.keys), frame, profiles.reach)
        sounding = [other for other in [*earlier, *later] if line.key_at(other) is not None]
        leak = sum(
            (profiles.energy_at(other - frame) * line.powers[other] for other in sounding),
            np.zeros(line.powers.shape[1]),
        )
        return cls(leak=leak, own=profiles.own_energy)

    def heard(
        self, keys: Sequence[Optional[NoteKey]], powers: np.ndarray  # pylint: disable=unused-argument
    ) -> np.ndarray:
        return np.asarray(self.own * powers)

    def gains(self, keys: Sequence[Optional[NoteKey]]) -> np.ndarray:
        return np.tile(self.own, (len(keys), 1))

    def extends(self, key: Optional[NoteKey]) -> bool:  # pylint: disable=unused-argument
        return False


def surroundings(line: ChannelLine, frame: int, profiles: FrameProfiles) -> ChannelSurroundings:
    """What ``line``'s other frames leave in ``frame``'s reading, read as the channel's kind adds its frames.

    Args:
        line: The channel's frames.
        frame: The frame being decided.
        profiles: How each bin's window weighs the frames around the one it reads.

    Returns:
        The frame's surroundings on the channel.
    """
    if line.coherent:
        return TonalSurroundings.around(line, frame, profiles)

    return NoiseSurroundings.around(line, frame, profiles)


def _window_sides(frames: int, frame: int, reach: int) -> Tuple[range, range]:
    """The frames the window of ``frame`` reads before it and after it, within a line of ``frames`` frames."""
    return range(max(0, frame - reach), frame), range(frame + 1, min(frames, frame + reach + 1))


def _joined_power(row: np.ndarray, before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """The power a row adds to a frame by joining the notes held beside it into one held note.

    The joined note reaches each bin with the sum of its parts' amplitudes, so it leaves
    ``(before + row + after)²`` in the reading, of which the leak already holds ``before²`` and
    ``after²``. The difference is written expanded, so those two squares are never added and taken
    back.

    Args:
        row: What each row reaches each bin with, in amplitude, one row per candidate.
        before: What the note held up to the frame reaches each bin with, zero for a row leaving it.
        after: What the note held from the frame reaches each bin with, zero for a row leaving it.

    Returns:
        The power each row adds, one row per candidate.
    """
    return np.asarray(np.square(row) + 2.0 * row * (before + after) + 2.0 * before * after)
