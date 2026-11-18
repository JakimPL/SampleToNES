from typing import Dict, Final, FrozenSet, List, Sequence, Tuple

import numpy as np

from assets.footage.mastering import decibel_gain, measure
from assets.footage.schedule import Schedule
from assets.footage.specification import Listening
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_core.audio.mixing import mix
from sampletones_core.constants.enums import AudioSourceType, ChannelName
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels
from sampletones_core.reconstructions.reconstruction.stems.hearing import (
    Hearing,
    heard_renders,
    offered_channels,
    selection_of,
)

CROSSFADE_SECONDS: Final[float] = 0.008
EDGE_FADE_SECONDS: Final[float] = 0.010

Piece = Tuple[np.ndarray, int, int]


class UnknownStemError(LookupError):
    """Raised when a listening names a stem the document holds no recording of."""


class ListeningAudio:
    """What the Reconstructions tab plays of one document under each listening.

    A listening ticks stem rows the way the Stems card does: a row ticked hears its recording on every
    channel it holds frames on. Reconstruction plays the channels heard and Original the recordings heard,
    each read with the functions the application plays them with.
    """

    def __init__(self, data: ReconstructionData) -> None:
        reconstruction = data.reconstruction
        stems_data = reconstruction.stems_data
        self._data = data
        self._channels = rendered_channels(reconstruction)
        self._mixed = mix(list(self._channels.values()))
        self._offered = offered_channels(stems_data)
        self._playing: FrozenSet[ChannelName] = frozenset(reconstruction.playing_channels)
        self._ids: Dict[str, int] = {
            name: entry.id for entry in stems_data.config.entries if (name := stems_data.named(entry.id)) is not None
        }

    def audio(self, listening: Listening) -> np.ndarray:
        """The audio the tab plays under ``listening``, from the document's first sample.

        Raises:
            UnknownStemError: If the listening names a stem the document holds no recording of.
        """
        hearing = self._hearing(listening.stems)
        match listening.source:
            case AudioSourceType.ORIGINAL:
                return mix(list(self._data.recordings_heard(hearing.selection)))
            case AudioSourceType.RECONSTRUCTION:
                return heard_renders(self._data.reconstruction, hearing, self._channels, self._mixed).playing

    def whole(self, source: AudioSourceType) -> np.ndarray:
        """The audio ``source`` plays with every stem row ticked."""
        return self.audio(Listening(source=source, stems=tuple(sorted(self._ids))))

    def _hearing(self, stems: Sequence[str]) -> Hearing:
        missing = [name for name in stems if name not in self._ids]
        if missing:
            raise UnknownStemError(f"The document holds no stem named {missing}; it holds {sorted(self._ids)}")

        heard = {self._ids[name]: self._offered[self._ids[name]] for name in stems}
        return Hearing(selection=selection_of(heard), channels_on=self._playing)


def soundtrack(
    audio: ListeningAudio,
    timeline_schedule: Schedule,
    *,
    frame_length: int,
    sample_rate: int,
) -> np.ndarray:
    """The footage's sound: each run's listening over the samples its frames show, cut together with
    equal-power crossfades on the frames where the listening changes.

    Frame ``i`` begins at the sample the playhead stands at in it, so a cut sounds where the picture changes.
    The reconstruction is raised or lowered to the original's loudness over the footage, so the two compare
    at one level.
    """
    start = timeline_schedule.tick(0) * frame_length
    end = timeline_schedule.tick(timeline_schedule.frame_count) * frame_length
    original = measure(audio.whole(AudioSourceType.ORIGINAL)[start:end], sample_rate)
    reconstruction = measure(audio.whole(AudioSourceType.RECONSTRUCTION)[start:end], sample_rate)
    gains = {
        AudioSourceType.ORIGINAL: 1.0,
        AudioSourceType.RECONSTRUCTION: decibel_gain(original.integrated - reconstruction.integrated),
    }
    rendered: Dict[Listening, np.ndarray] = {}
    pieces: List[Piece] = []
    for run in timeline_schedule.runs:
        if run.listening not in rendered:
            whole = np.zeros(end, dtype=np.float64)
            sounding = audio.audio(run.listening)[:end]
            whole[: len(sounding)] = sounding * gains[run.listening.source]
            rendered[run.listening] = whole[start:end]

        first = timeline_schedule.tick(run.first) * frame_length - start
        last = timeline_schedule.tick(run.last) * frame_length - start
        pieces.append((rendered[run.listening], first, last))

    return assembled(
        pieces,
        length=end - start,
        crossfade=round(CROSSFADE_SECONDS * sample_rate),
        edge_fade=round(EDGE_FADE_SECONDS * sample_rate),
    )


def assembled(pieces: Sequence[Piece], *, length: int, crossfade: int, edge_fade: int) -> np.ndarray:
    """Pieces of ``length``-sample audio, each heard from its first sample up to its last, joined by equal-power
    crossfades ``crossfade`` samples wide, the whole faded in and out over ``edge_fade`` samples.
    """
    positions = np.arange(length, dtype=np.float64)
    output = np.zeros(length, dtype=np.float64)
    for audio, first, last in pieces:
        gain = np.ones(length, dtype=np.float64)
        if first > 0:
            gain *= np.sin(crossfade_phase(positions, first, crossfade))

        if last < length:
            gain *= np.cos(crossfade_phase(positions, last, crossfade))

        output += audio * gain

    output[:edge_fade] *= np.linspace(0.0, 1.0, edge_fade)
    output[length - edge_fade :] *= np.linspace(1.0, 0.0, edge_fade)
    return output


def crossfade_phase(positions: np.ndarray, cut: int, width: int) -> np.ndarray:
    """The quarter-turn phase of an equal-power crossfade ``width`` samples wide, centered on the sample ``cut``."""
    return np.clip((positions - (cut - width / 2)) / width, 0.0, 1.0) * np.pi / 2
