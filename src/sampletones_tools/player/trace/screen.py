from typing import Final

from sampletones_player.compression.decode import decode_planes
from sampletones_player.information import ProgramInformation
from sampletones_player.rom.clock import ProgramClock
from sampletones_player.rom.program import SCREEN_TEXT
from sampletones_player.song import Song
from sampletones_player.specification.compression import PITCH_INDEX_MASK
from sampletones_player.specification.planes import SILENT_PITCH_INDEX
from sampletones_player.specification.registers import DUTY_CYCLE_SHIFT, NOISE_MODE_SHIFT
from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.graphics.deck.state import (
    DUTY_COUNT,
    LAST_PITCH,
    MAX_LEVEL,
    NOISE_PERIOD_COUNT,
    DeckState,
    NoiseState,
    PulseState,
    Transport,
    TriangleState,
)
from sampletones_tools.player.graphics.picture.picture import Picture
from sampletones_tools.player.trace.clock import NO_FRAMES, CartridgeClock
from sampletones_tools.player.trace.trace import FIRST_TICK

LEVEL_MASK: Final[int] = MAX_LEVEL
DUTY_MASK: Final[int] = DUTY_COUNT - 1
NOISE_PERIOD_MASK: Final[int] = NOISE_PERIOD_COUNT - 1
SHORT_NOISE_FLAG: Final[int] = 1 << NOISE_MODE_SHIFT
RESTING_PITCH: Final[int] = 0


class ScreenTrace:
    """The screen a correct cartridge shows of a song once START has paused it.

    The shell draws its readings from the plane values the driver holds and from its own count of
    the frames played, and a pause holds both still, so a paused screen settles on one frame's
    state once the shell has composed every reading. That state is worked out here from the song,
    the shell's clock arithmetic and the text the screen gives room to, and drawn by the deck the
    shell's tables are built from.
    """

    def __init__(self, song: Song, information: ProgramInformation, deck: Deck) -> None:
        self._song = song
        self._shown = information.fitted(SCREEN_TEXT)
        self._deck = deck
        self._planes = decode_planes(song.planes).planes
        self._program = ProgramClock.of(song)

    def paused_after(self, played: int) -> Picture:
        """The picture the screen settles on once the song is paused after ``played`` frames.

        Args:
            played: The frames the song played before the pause, at least 0.

        Returns:
            Picture: The screen, its readings, its markers and its labels.

        Raises:
            ValueError: If ``played`` is negative.
        """
        return self._deck.showing(self.state_paused_after(played))

    def state_paused_after(self, played: int) -> DeckState:
        """What the screen shows once the song is paused after ``played`` frames.

        The channels show the tick the last played frame left the driver on, and a song that has
        ended shows its final tick. The clock, the progress bar and the noise shape's turn stand
        where the shell's own count of those frames put them.

        Raises:
            ValueError: If ``played`` is negative.
        """
        clock = CartridgeClock.after(self._program, played)
        tick = self._tick(played)
        planes = self._planes
        return DeckState(
            title=self._shown.title,
            artist=self._shown.artist,
            copyright=self._shown.copyright,
            pulse1=self._pulse(planes.pulse1_control[tick], planes.pulse1_value[tick]),
            pulse2=self._pulse(planes.pulse2_control[tick], planes.pulse2_value[tick]),
            triangle=self._triangle(planes.triangle_value[tick]),
            noise=self._noise(planes.noise_control[tick], planes.noise_value[tick]),
            played_seconds=clock.seconds,
            total_seconds=ProgramClock.seconds_at(self._program.total_frames),
            progress=clock.progress_pixels,
            transport=Transport.STOPPED if clock.ended else Transport.PAUSED,
            shimmer=clock.shimmer,
        )

    def _tick(self, played: int) -> int:
        if played == NO_FRAMES:
            return FIRST_TICK

        tick = self._song.tick_at(played - 1)
        return self._song.ticks - 1 if tick is None else tick

    @staticmethod
    def _pulse(control: int, value: int) -> PulseState:
        """A pulse channel's reading; a resting one hides its pitch, so its pitch is held within the table."""
        level = control & LEVEL_MASK
        pitch = value & PITCH_INDEX_MASK
        return PulseState(
            duty=(control >> DUTY_CYCLE_SHIFT) & DUTY_MASK,
            level=level,
            pitch=pitch if level else min(pitch, LAST_PITCH),
        )

    @staticmethod
    def _triangle(value: int) -> TriangleState:
        pitch = value & PITCH_INDEX_MASK
        sounding = pitch != SILENT_PITCH_INDEX
        return TriangleState(sounding=sounding, pitch=pitch if sounding else RESTING_PITCH)

    @staticmethod
    def _noise(control: int, value: int) -> NoiseState:
        return NoiseState(
            level=control & LEVEL_MASK,
            period=value & NOISE_PERIOD_MASK,
            short=bool(value & SHORT_NOISE_FLAG),
        )
