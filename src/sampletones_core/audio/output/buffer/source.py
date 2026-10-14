import threading
from typing import Final, Optional

import numpy as np

from sampletones_core.audio.output.source import FailureReport, Fill, Tagged
from sampletones_core.constants.audio import START_OF_AUDIO

from .resampler import BlockResampler

FEED_FRAMES: Final[int] = 1024


class BufferSource:
    """A document's audio, kept at the rate it was made at and read in blocks at the device's rate.

    The audio is resampled as it is read, so a sound keeps its pitch and its length on a device of any rate,
    and a sound already at the device's rate is read sample for sample. The source begins at the rate of the
    stream it plays on. Every block reports the document sample the playback reached, which output sample
    ``k`` past a seek places at the seek plus ``k * sample_rate / output_rate``.

    A seek and a replacement are its owner's commands, so they run on the writer's thread between reads and
    take effect at the next block. A seek moves to a document sample. A replacement keeps the playback where
    it stands in time, mapped onto the new audio's rate, so an edit landing during playback goes on from the
    moment the listener reached.
    """

    def __init__(
        self,
        audio: np.ndarray,
        *,
        sample_rate: int,
        start: int,
    ) -> None:
        """Holds the audio and the place the playback starts at.

        Args:
            audio: The document's samples, one channel.
            sample_rate: The rate the audio was made at.
            start: The document sample the playback starts at, clamped to the audio.
        """
        self._closed = threading.Event()
        self._audio: np.ndarray = _prepared(audio)
        self._sample_rate = sample_rate
        self._output_rate = sample_rate
        self._resampler: Optional[BlockResampler] = None
        self._anchor: int = START_OF_AUDIO
        self._fed: int = START_OF_AUDIO
        self._delivered: int = 0
        self._move_to(start)

    @property
    def position(self) -> int:
        """The document sample the audio read so far reaches."""
        return min(
            len(self._audio),
            self._anchor + round(self._delivered * self._sample_rate / self._output_rate),
        )

    def begin(self, output_rate: int, _failed: FailureReport) -> None:
        """Takes the rate the stream plays at, resampling the audio to it from the place the playback stands.

        The audio is read on the writer's thread alone, so a failure reaches the writer as its read raises.
        """
        self._output_rate = output_rate
        self._resampler = self._resampler_for(self._sample_rate)
        self._move_to(self.position)

    def read_into(self, block: np.ndarray) -> Fill[int]:
        """Fills ``block`` with the next audio at the device's rate, reporting the document sample reached."""
        if self._closed.is_set():
            return Fill(frames=0, reports=())

        frames = self._direct_into(block) if self._resampler is None else self._resampled_into(block, self._resampler)
        self._delivered += frames
        reports = (Tagged(offset=frames, report=self.position),) if frames else ()
        return Fill(frames=frames, reports=reports)

    def seek(self, position: int) -> None:
        """Moves the playback to a document sample, clamped to the audio, from the next block."""
        self._move_to(position)

    def replace(self, audio: np.ndarray, *, sample_rate: int) -> None:
        """Swaps the audio from the next block, keeping the moment the playback reached."""
        moment = self.position / self._sample_rate
        self._audio = _prepared(audio)
        if sample_rate != self._sample_rate:
            self._sample_rate = sample_rate
            self._resampler = self._resampler_for(sample_rate)

        self._move_to(round(moment * sample_rate))

    def close(self) -> None:
        """Ends the sound: every read from now on comes up empty."""
        self._closed.set()

    def _move_to(self, position: int) -> None:
        self._anchor = max(START_OF_AUDIO, min(position, len(self._audio)))
        self._fed = self._anchor
        self._delivered = 0
        if self._resampler is not None:
            self._resampler.restart()

    def _direct_into(self, block: np.ndarray) -> int:
        frames = min(len(block), len(self._audio) - self._fed)
        block[:frames] = self._audio[self._fed : self._fed + frames]
        self._fed += frames
        return frames

    def _resampled_into(self, block: np.ndarray, resampler: BlockResampler) -> int:
        while resampler.wants(len(block)):
            chunk = self._audio[self._fed : self._fed + FEED_FRAMES]
            self._fed += len(chunk)
            resampler.feed(chunk, last=self._fed >= len(self._audio))

        output = resampler.take(len(block))
        block[: len(output)] = output
        return len(output)

    def _resampler_for(self, sample_rate: int) -> Optional[BlockResampler]:
        if sample_rate == self._output_rate:
            return None

        return BlockResampler(input_rate=sample_rate, output_rate=self._output_rate)


def _prepared(audio: np.ndarray) -> np.ndarray:
    """The samples as one contiguous run of 32-bit floats, the form the resampler and the device take."""
    return np.ascontiguousarray(audio, dtype=np.float32)
