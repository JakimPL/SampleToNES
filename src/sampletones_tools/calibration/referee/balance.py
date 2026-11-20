import math
from typing import Dict, Final, Mapping, Optional, Sequence

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import render_channels
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels
from sampletones_tools.calibration.corpus.truth import PitchLine, Truth, sounding_pitches

from .frames import common_length
from .pitch import SEMITONES_PER_OCTAVE
from .protocol import Judgment
from .scale import effective_scale

BALANCE_REFEREE: Final[str] = "balance"
PULSES: Final[str] = "pulses"
TRIANGLE: Final[str] = "triangle"
NOISE: Final[str] = "noise"
BASS_ON_A_PULSE: Final[str] = "bass-on-pulse"
SCALE: Final[str] = "scale"

PARTS: Final[Dict[str, Sequence[ChannelName]]] = {
    PULSES: (ChannelName.PULSE1, ChannelName.PULSE2),
    TRIANGLE: (ChannelName.TRIANGLE,),
    NOISE: (ChannelName.NOISE,),
}


class BalanceReferee:
    """Reads how a conversion shares the sound out among the channels, against how the sound itself does.

    Each part's share is its energy over the energy of every part, the two pulses one part since they
    sound the same mix whichever carries which line. The score is the share that would have to move
    between parts to match the sound, half the summed differences. The readings behind it are:

    - each part's share played less its share written, so a starved triangle reads below zero;
    - ``bass-on-pulse``: the share of the triangle's sounding frames whose note a pulse plays, in any
      octave, while the triangle plays another or none;
    - ``scale``: how much the conversion scaled the sound before matching it, one where it matched
      the sound at the level the channels play it.
    """

    @property
    def name(self) -> str:
        return BALANCE_REFEREE

    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]:
        """How ``reconstruction`` shares the sound out among the channels, against ``truth``.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` for a sound written as no frames.
        """
        if not truth.instructions:
            return None

        written = _shares(render_channels(truth.instructions, reconstruction.config))
        played = _shares(rendered_channels(reconstruction))
        differences = {part: played[part] - written[part] for part in PARTS}
        components = {
            **differences,
            BASS_ON_A_PULSE: bass_on_pulse(
                sounding_pitches(truth.instructions, reconstruction.config),
                sounding_pitches(reconstruction.instructions, reconstruction.config),
            ),
            SCALE: effective_scale(reconstruction),
        }
        return Judgment(score=sum(abs(value) for value in differences.values()) / 2, components=components)


def bass_on_pulse(
    written: Mapping[ChannelName, PitchLine],
    played: Mapping[ChannelName, PitchLine],
) -> float:
    """The share of the written triangle's sounding frames whose note a played pulse sounds instead.

    A pulse counts where it sounds the triangle's note in any octave while the played triangle
    sounds another note or none.
    """
    bass = written.get(ChannelName.TRIANGLE, ())
    if not bass:
        return 0.0

    triangle = played.get(ChannelName.TRIANGLE, ())
    pulses = [played[channel] for channel in PARTS[PULSES] if played.get(channel)]
    length = common_length(bass, triangle, *pulses)
    sounding = [frame for frame in range(length) if bass[frame] is not None]
    if not sounding:
        return 0.0

    taken = 0
    for frame in sounding:
        target = bass[frame]
        if triangle and _same_note_class(triangle[frame], target):
            continue
        taken += any(_same_note_class(line[frame], target) for line in pulses)

    return taken / len(sounding)


def _same_note_class(frequency: Optional[float], target: Optional[float]) -> bool:
    if frequency is None or target is None:
        return False

    return round(SEMITONES_PER_OCTAVE * math.log2(frequency / target)) % SEMITONES_PER_OCTAVE == 0


def _shares(channel_audio: Mapping[ChannelName, np.ndarray]) -> Dict[str, float]:
    """Each part's share of the energy the channels render together."""
    energies = {
        part: sum(float(np.sum(np.square(channel_audio[channel]))) for channel in channels if channel in channel_audio)
        for part, channels in PARTS.items()
    }
    total = sum(energies.values())
    return {part: energy / total if total else 0.0 for part, energy in energies.items()}
