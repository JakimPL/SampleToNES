import numpy as np

from sampletones_application.logic.shared.synthesis import ChannelBank, synthesize_tick
from sampletones_core.audio import clip_audio_inplace, silence
from sampletones_core.performance import LiveNote


class SoundingNote:
    """A live note synthesized on a tick grid of its own, from its strike, and handed out in blocks of any length.

    The grid starts at the strike, so the note's first tick opens the first block after it, and each channel
    the note sounds on starts its generator from rest, as a row starting a note does. Each tick sums the
    note's channels and clips them, as a row's ticks are mixed. The note owns its grid and the tick waiting
    to be handed out, so a mix could sum several notes, each on generators of its own.
    """

    def __init__(self, note: LiveNote, bank: ChannelBank) -> None:
        """Strikes ``note`` on the generators of ``bank``.

        Args:
            note: The note struck.
            bank: The generators and the tick clock at the stream's rate, held by the note alone while it sounds.
        """
        self._note = note
        self._bank = bank
        self._tick_index: int = 0
        self._tick: np.ndarray = silence(0)
        self._handed: int = 0
        for channel_name in note.channel_names:
            bank.generator(channel_name).reset()

    @property
    def finished(self) -> bool:
        """Whether the note has handed out its last sample."""
        return self._handed == len(self._tick) and self._note.finished

    def fill(self, block: np.ndarray) -> int:
        """Writes the note's next samples into ``block``, from its start, answering how many it wrote.

        The note fills the block whole while it sounds, and short once its last tick is handed out.
        """
        frames = 0
        while frames < len(block):
            if self._handed == len(self._tick):
                if self._note.finished:
                    break

                self._tick = self._next_tick()
                self._handed = 0

            count = min(len(block) - frames, len(self._tick) - self._handed)
            block[frames : frames + count] = self._tick[self._handed : self._handed + count]
            frames += count
            self._handed += count

        return frames

    def release(self) -> None:
        """Ends the note at once, as a note-off row does, leaving the rest of its tick unheard."""
        self._note.release()
        self._tick = silence(0)
        self._handed = 0

    def _next_tick(self) -> np.ndarray:
        frame_length = self._bank.clock.frame_length(self._tick_index)
        self._tick_index += 1
        audio = silence(frame_length)
        for channel_name, instruction in self._note.tick().items():
            audio += synthesize_tick(self._bank.generator(channel_name), instruction, frame_length)

        return clip_audio_inplace(audio)
