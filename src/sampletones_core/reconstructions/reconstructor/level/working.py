from typing import Callable, Dict, Mapping, Protocol, Sequence

import numpy as np

from sampletones_core.audio import active_frame_level, mix
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import MINIMUM_AUDIO_LEVEL
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, LevelMethod
from sampletones_core.fft import Window
from sampletones_core.generators import FULL_SCALE_RMS_LEVELS, GeneratorUnion
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig

from .fitted import LevelFitter


class WorkingLevel(Protocol):
    """The working level a run matches at: the coefficient its recordings are divided by before matching.

    A run reads the level once, on every recording it converts, so one factor scales the whole set.
    The run builds its matching machinery for the recordings' length, so a level reading the
    recordings through it receives it with them.
    """

    def coefficient(self, recordings: Sequence[np.ndarray], stems_config: StemsConfig, matcher: FrameMatcher) -> float:
        """The positive coefficient the run's recordings are divided by.

        Args:
            recordings: Every stem's loaded recording, in entry order.
            stems_config: The stems setup the run is made under.
            matcher: The matching machinery the run matches the recordings with.
        """


WorkingLevelFactory = Callable[[Config, Mapping[ChannelName, GeneratorUnion], Window], WorkingLevel]


class LoudnessLevel:
    """The working level the frames' loudness sets, bringing the recordings' typical frame to what one channel renders.

    The typical frame is read on the recordings' mix: the robust active-frame RMS level under the
    configured percentile and audibility floor, floored at ``MINIMUM_AUDIO_LEVEL`` so a silent mix
    yields a finite coefficient. It is brought to the full-scale RMS level of the quietest tone
    channel the setup covers, or of the quietest covered channel when the setup covers no tone
    channel. A steady tone then plays at a level a single tone channel renders whole, so one channel
    can answer it, and louder frames call on more channels. A pulse and the noise swing between two
    levels, so their RMS level is their peak; a triangle's is its peak over the square root of three.

    Attributes:
        config: The configuration setting the frame length, the percentile and the audibility floor.
        channels: The run's channels, whose generators give each channel's full-scale RMS level.
    """

    def __init__(self, config: Config, channels: Mapping[ChannelName, GeneratorUnion]) -> None:
        self.config = config
        self.channels: Dict[ChannelName, GeneratorUnion] = dict(channels)

    def coefficient(
        self,
        recordings: Sequence[np.ndarray],
        stems_config: StemsConfig,
        matcher: FrameMatcher,  # pylint: disable=unused-argument
    ) -> float:
        return float(self._typical_level(mix(list(recordings))) / self._anchor_level(stems_config))

    def _typical_level(self, audio: np.ndarray) -> float:
        """The robust RMS level of ``audio``'s typical audible frame, at least ``MINIMUM_AUDIO_LEVEL``."""
        general = self.config.general
        return max(
            active_frame_level(
                audio,
                self.config.library.frame_length,
                percentile=general.coefficient_percentile,
                audibility_floor=general.coefficient_audibility_floor,
            ),
            MINIMUM_AUDIO_LEVEL,
        )

    def _anchor_level(self, stems_config: StemsConfig) -> float:
        """The full-scale RMS level of the quietest covered tone channel, or covered channel without one."""
        covered = [name for name in self.channels if name in stems_config.covered_channels]
        anchors = [name for name in covered if name in TONE_CHANNELS] or covered
        return min(FULL_SCALE_RMS_LEVELS[self.channels[name].class_name()] for name in anchors)


class FittedLevel:
    """The loudness level moved onto a triangle line the recordings hold.

    The triangle plays one level, so a bass line plays on it only where the working level brings the
    line there. The recordings are first read at the loudness level, and :class:`LevelFitter` reads
    the factor that moves it onto the line. The level is the loudness level times that factor, and
    the loudness level itself where the fitter finds none.

    Attributes:
        loudness: The level the recordings are first read at.
        config: The configuration the fitter frames the recordings under.
        channels: The run's channels.
        window: The analysis window the fitter frames the recordings with.
    """

    def __init__(
        self,
        loudness: LoudnessLevel,
        config: Config,
        channels: Mapping[ChannelName, GeneratorUnion],
        window: Window,
    ) -> None:
        self.loudness = loudness
        self.config = config
        self.channels: Dict[ChannelName, GeneratorUnion] = dict(channels)
        self.window = window

    def coefficient(self, recordings: Sequence[np.ndarray], stems_config: StemsConfig, matcher: FrameMatcher) -> float:
        coefficient = self.loudness.coefficient(recordings, stems_config, matcher)
        fitter = LevelFitter(stems_config, self.channels, matcher, self.config, self.window)
        factor = fitter.factor(self._by_stem(recordings, stems_config), coefficient)
        return coefficient if factor is None else coefficient * factor

    @staticmethod
    def _by_stem(recordings: Sequence[np.ndarray], stems_config: StemsConfig) -> Dict[int, np.ndarray]:
        """Each recording keyed by the id of the entry it was loaded for."""
        return {entry.id: recording for entry, recording in zip(stems_config.entries, recordings)}


def working_level(config: Config, channels: Mapping[ChannelName, GeneratorUnion], window: Window) -> WorkingLevel:
    """The working level ``config.general.level`` names, over the run's ``channels`` and framed with ``window``.

    Under ``coefficient`` it is the loudness level, and under ``fitted`` the loudness level moved onto a
    triangle line the recordings hold.
    """
    loudness = LoudnessLevel(config, channels)
    match config.general.level:
        case LevelMethod.COEFFICIENT:
            return loudness
        case LevelMethod.FITTED:
            return FittedLevel(loudness, config, channels, window)
