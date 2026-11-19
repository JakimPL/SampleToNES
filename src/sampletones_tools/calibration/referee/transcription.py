from dataclasses import dataclass, field
from typing import Dict, Final, List, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth

from .frames import Frame, channel_streams, common_length, sounds
from .protocol import Judgment

TRANSCRIPTION_REFEREE: Final[str] = "transcription"
MISSED: Final[str] = "missed"
SPURIOUS: Final[str] = "spurious"
NOTE: Final[str] = "note"
VOLUME: Final[str] = "volume"
DUTY: Final[str] = "duty"
PERIOD: Final[str] = "period"
MODE: Final[str] = "mode"

PULSES: Final[Tuple[ChannelName, ChannelName]] = (ChannelName.PULSE1, ChannelName.PULSE2)
SOLE_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.TRIANGLE, ChannelName.NOISE)


@dataclass
class Tally:
    """The channel-frames a transcription counts, and those that miss in each way."""

    counted: int = 0
    wrong: int = 0
    written: int = 0
    missed: int = 0
    played: int = 0
    spurious: int = 0
    asked: Dict[str, int] = field(default_factory=dict)
    disagreed: Dict[str, int] = field(default_factory=dict)

    def add(self, written: Frame, played: Frame, *, volume_tolerance: int) -> None:
        """Counts one channel-frame, where the writing or the conversion sounds it."""
        written_sounds, played_sounds = sounds(written), sounds(played)
        if not written_sounds and not played_sounds:
            return

        self.counted += 1
        self.written += written_sounds
        self.played += played_sounds
        self.missed += written_sounds and not played_sounds
        self.spurious += played_sounds and not written_sounds
        if not (written_sounds and played_sounds):
            self.wrong += 1
            return

        fields = compared_fields(written, played, volume_tolerance=volume_tolerance)
        for name, agrees in fields.items():
            self.asked[name] = self.asked.get(name, 0) + 1
            self.disagreed[name] = self.disagreed.get(name, 0) + (not agrees)

        self.wrong += not all(fields.values())

    def judgment(self) -> Optional[Judgment]:
        """The share of counted channel-frames played otherwise than written, and the readings behind it.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` where neither side sounded a frame to count.
        """
        if not self.counted:
            return None

        components: Dict[str, float] = {}
        if self.written:
            components[MISSED] = self.missed / self.written
        if self.played:
            components[SPURIOUS] = self.spurious / self.played
        for name, asked in self.asked.items():
            components[name] = self.disagreed[name] / asked

        return Judgment(score=self.wrong / self.counted, components=components)


class TranscriptionReferee:
    """Reads how much of a sound written as NES frames its conversion plays as written.

    A channel-frame counts where the writing or the conversion sounds it, so a channel the writing
    leaves silent and the conversion sounds counts against it. A counted frame is played as written
    where both sound it and every field the channel takes agrees, the volume within the tolerance.
    The two pulses sound one mix whichever of them carries which line, so each frame pairs them the
    way fewer fields disagree.

    The score is the share of counted channel-frames played otherwise. The readings behind it are the
    share of written frames left silent (``missed``), the share of played frames the writing leaves
    silent (``spurious``), and for each field, the share of frames both sound where it disagrees.
    """

    def __init__(self, *, volume_tolerance: int) -> None:
        self._volume_tolerance = volume_tolerance

    @property
    def name(self) -> str:
        return TRANSCRIPTION_REFEREE

    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]:
        """The share of counted channel-frames ``reconstruction`` plays otherwise than ``truth`` writes them.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` for a sound written as no frames.
        """
        if not truth.instructions:
            return None

        played_streams = reconstruction.instructions
        length = common_length(*truth.instructions.values(), *played_streams.values())
        written = channel_streams(truth.instructions, length)
        played = channel_streams(played_streams, length)
        tally = Tally()
        for frame in range(length):
            pairs = self._paired_pulses(written, played, frame)
            pairs.extend((written[channel][frame], played[channel][frame]) for channel in SOLE_CHANNELS)
            for written_frame, played_frame in pairs:
                tally.add(written_frame, played_frame, volume_tolerance=self._volume_tolerance)

        return tally.judgment()

    def _paired_pulses(
        self,
        written: Dict[ChannelName, Tuple[Frame, ...]],
        played: Dict[ChannelName, Tuple[Frame, ...]],
        frame: int,
    ) -> List[Tuple[Frame, Frame]]:
        first, second = PULSES
        straight = [(written[first][frame], played[first][frame]), (written[second][frame], played[second][frame])]
        crossed = [(written[first][frame], played[second][frame]), (written[second][frame], played[first][frame])]
        return crossed if self._disagreements(crossed) < self._disagreements(straight) else straight

    def _disagreements(self, pairs: List[Tuple[Frame, Frame]]) -> int:
        """How many fields disagree across the pairs, a frame sounding on one side alone counting one."""
        count = 0
        for written_frame, played_frame in pairs:
            if sounds(written_frame) and sounds(played_frame):
                fields = compared_fields(written_frame, played_frame, volume_tolerance=self._volume_tolerance)
                count += sum(not agrees for agrees in fields.values())
            else:
                count += sounds(written_frame) != sounds(played_frame)

        return count


def compared_fields(written: Frame, played: Frame, *, volume_tolerance: int) -> Dict[str, bool]:
    """Whether each field the channel takes agrees between two sounding frames of it."""
    match written, played:
        case PulseInstruction(), PulseInstruction():
            return {
                NOTE: written.pitch == played.pitch,
                DUTY: written.duty_cycle == played.duty_cycle,
                VOLUME: abs(written.volume - played.volume) <= volume_tolerance,
            }
        case TriangleInstruction(), TriangleInstruction():
            return {NOTE: written.pitch == played.pitch}
        case NoiseInstruction(), NoiseInstruction():
            return {
                PERIOD: written.period == played.period,
                MODE: written.short == played.short,
                VOLUME: abs(written.volume - played.volume) <= volume_tolerance,
            }
        case _:
            raise TypeError(f"Frames of different channels compared: {written!r} and {played!r}")
