from dataclasses import dataclass
from typing import NamedTuple, Self

from sampletones_core.configs import Config
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction


class _Reading(NamedTuple):
    """What a change between two frames of one channel is charged on: where it sounds, how loud and in what timbre.

    A pulse or the triangle sounds at a pitch and the noise at a period, so both read as the place the
    channel sounds. A pulse's duty cycle and the noise's mode are its timbre, and the triangle's one
    level and one timbre read alike on every frame.
    """

    place: int
    volume: int
    timbre: int


@dataclass(frozen=True)
class TransitionWeights:
    """What a decoder charges a channel for changing what it plays from one frame to the next.

    Attributes:
        pitch: The charge per semitone of pitch, or per step of the noise's period.
        volume: The charge per step of volume.
        timbre: The charge for a change of duty cycle or of the noise's mode.
        on_off: The charge for a channel starting or falling silent.
    """

    pitch: float
    volume: float
    timbre: float
    on_off: float

    @classmethod
    def of(cls, config: Config) -> Self:
        """The weights the configuration's decoder settings name."""
        decoder = config.generation.decoder
        return cls(
            pitch=decoder.pitch_weight,
            volume=decoder.volume_weight,
            timbre=decoder.timbre_weight,
            on_off=decoder.on_off_weight,
        )


def transition_cost(previous: InstructionUnion, current: InstructionUnion, weights: TransitionWeights) -> float:
    """What one channel pays to move from ``previous`` to ``current`` between two frames.

    Two silent frames cost nothing, a channel starting or falling silent costs the on-off weight, and
    a channel sounding on both frames pays for every semitone or period step it moves, every step of
    volume and a change of timbre.

    Raises:
        TypeError: If the two instructions belong to different kinds of channel.
    """
    if type(previous) is not type(current):
        raise TypeError(f"A channel moves between instructions of one kind, not {previous!r} and {current!r}")

    if not previous.on and not current.on:
        return 0.0

    if previous.on != current.on:
        return weights.on_off

    before, after = _reading(previous), _reading(current)
    return (
        weights.pitch * float(abs(before.place - after.place))
        + weights.volume * float(abs(before.volume - after.volume))
        + weights.timbre * float(before.timbre != after.timbre)
    )


def _reading(instruction: InstructionUnion) -> _Reading:
    """The place, volume and timbre a sounding instruction is charged on."""
    match instruction:
        case PulseInstruction():
            return _Reading(place=instruction.pitch, volume=instruction.volume, timbre=instruction.duty_cycle)
        case TriangleInstruction():
            return _Reading(place=instruction.pitch, volume=0, timbre=0)
        case NoiseInstruction():
            return _Reading(place=instruction.period, volume=instruction.volume, timbre=int(instruction.short))
        case _:
            raise TypeError(f"Unknown instruction {instruction!r}")
