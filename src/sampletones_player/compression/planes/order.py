from __future__ import annotations

from typing import Iterable, NamedTuple

from sampletones_player.specification.compression import PLANE_COUNT


class PlaneOrder(NamedTuple):
    """One byte series per plane, in the order the song block writes them.

    The song block states its planes as a run of eight, and both readings of a song take that
    shape: the values each plane plays tick by tick, and the tokens those values are written as.
    Naming the eight is what lets either be carried whole and read back by the channel it
    belongs to.

    Attributes:
        pulse1_control: The first pulse channel's timbre and volume.
        pulse1_value: The first pulse channel's pitch.
        pulse2_control: The second pulse channel's timbre and volume.
        pulse2_value: The second pulse channel's pitch.
        triangle_control: The triangle channel's linear counter.
        triangle_value: The triangle channel's pitch.
        noise_control: The noise channel's timbre and volume.
        noise_value: The noise channel's period.
    """

    pulse1_control: bytes
    pulse1_value: bytes
    pulse2_control: bytes
    pulse2_value: bytes
    triangle_control: bytes
    triangle_value: bytes
    noise_control: bytes
    noise_value: bytes

    @classmethod
    def across(cls, planes: Iterable[bytes]) -> PlaneOrder:
        """Gathers a song's planes under the names the song block writes them by.

        Args:
            planes: The planes, in the order the song block writes them.

        Returns:
            PlaneOrder: The planes, each under its own name.

        Raises:
            ValueError: If the planes given are other than the ones a song block holds.
        """
        gathered = tuple(planes)
        if len(gathered) != PLANE_COUNT:
            raise ValueError(f"a song block holds {PLANE_COUNT} planes, and these are {len(gathered)}")

        return cls._make(gathered)
