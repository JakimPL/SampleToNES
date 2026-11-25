from typing import Final, List, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.config.notes import NotesConfig

from .families import Family
from .item import CorpusItem
from .nes import held, written_item

PULSE_CATEGORY: Final[str] = "notes-pulse"
TRIANGLE_CATEGORY: Final[str] = "notes-triangle"
NOISE_CATEGORY: Final[str] = "notes-noise"
NOTE_CATEGORIES: Final[Tuple[str, ...]] = (PULSE_CATEGORY, TRIANGLE_CATEGORY, NOISE_CATEGORY)
NOISE_MODES: Final[Tuple[bool, bool]] = (False, True)


def build_notes(config: Config, *, grid: NotesConfig) -> List[CorpusItem]:
    """Every single note of the grid: the pulse's, the triangle's, and the noise channel's.

    A pulse note sounds at every pitch, volume and duty cycle of the grid, with one of the
    alternating duty cycles joining each pitch in turn. A triangle note sounds at every pitch. A
    noise note sounds at every period, in the long mode and then the short, at every volume. Each is
    held, then silent, so a conversion answers both its sound and its end. The page lists the loudest
    notes at every stride of pitches or periods; a triangle note sounds at its one level, so it is
    listed at every stride.

    Args:
        config: The configuration the notes are rendered at, the one the run converts with.
        grid: The grid the notes are laid on.

    Returns:
        List[CorpusItem]: The pulse notes, then the triangle notes, then the noise notes.
    """
    return [*_pulse_notes(config, grid), *_triangle_notes(config, grid), *_noise_notes(config, grid)]


def _pulse_notes(config: Config, grid: NotesConfig) -> List[CorpusItem]:
    loudest = max(grid.volumes)
    items: List[CorpusItem] = []
    for index, pitch in enumerate(grid.pitches):
        for duty_cycle in [*grid.duty_cycles, *_alternating(grid, index)]:
            for volume in grid.volumes:
                instruction = PulseInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=duty_cycle)
                items.append(
                    written_item(
                        f"note-pulse-p{pitch}-d{duty_cycle}-v{volume}",
                        Family.NOTES,
                        PULSE_CATEGORY,
                        listed=_listed(index, grid.listed_pitch_stride, loudest=volume == loudest),
                        instructions={ChannelName.PULSE1: _held(ChannelName.PULSE1, instruction, grid)},
                        config=config,
                    )
                )

    return items


def _triangle_notes(config: Config, grid: NotesConfig) -> List[CorpusItem]:
    return [
        written_item(
            f"note-triangle-p{pitch}",
            Family.NOTES,
            TRIANGLE_CATEGORY,
            listed=_listed(index, grid.listed_pitch_stride, loudest=True),
            instructions={
                ChannelName.TRIANGLE: _held(ChannelName.TRIANGLE, TriangleInstruction(on=True, pitch=pitch), grid)
            },
            config=config,
        )
        for index, pitch in enumerate(grid.pitches)
    ]


def _noise_notes(config: Config, grid: NotesConfig) -> List[CorpusItem]:
    loudest = max(grid.volumes)
    items: List[CorpusItem] = []
    for short in NOISE_MODES:
        for period in range(MAX_PERIOD + 1):
            for volume in grid.volumes:
                instruction = NoiseInstruction(on=True, period=period, volume=volume, short=short)
                items.append(
                    written_item(
                        f"note-noise-{'short' if short else 'long'}-p{period}-v{volume}",
                        Family.NOTES,
                        NOISE_CATEGORY,
                        listed=_listed(period, grid.listed_noise_period_stride, loudest=volume == loudest),
                        instructions={ChannelName.NOISE: _held(ChannelName.NOISE, instruction, grid)},
                        config=config,
                    )
                )

    return items


def _alternating(grid: NotesConfig, index: int) -> List[int]:
    """The alternating duty cycle the pitch at ``index`` takes, in turn with its neighbors.

    The alternating duty cycles are timbres the ear hears alike, so each pitch takes one of them,
    which covers both across the grid at the cost of one.
    """
    if not grid.alternating_duty_cycles:
        return []

    return [grid.alternating_duty_cycles[index % len(grid.alternating_duty_cycles)]]


def _listed(step: int, stride: int, *, loudest: bool) -> bool:
    """Whether the page lists a note at ``step`` of its grid: the loudest, at every ``stride`` steps."""
    return loudest and step % stride == 0


def _held(channel: ChannelName, instruction: InstructionUnion, grid: NotesConfig) -> List[InstructionUnion]:
    return held(channel, instruction, sounding=grid.sounding_frames, silent=grid.silent_frames)
