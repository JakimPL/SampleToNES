from typing import Final, List, Tuple

import numpy as np

from sampletones_core.audio.processing import clip_audio
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, ordered_channels
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.config.truth import TruthConfig
from sampletones_tools.synthesis.voice.layer import Layer

from .families import Catalog, Family
from .item import CorpusItem, StemsSources
from .stems import mixed, side_by_side
from .synthesis import Probe, RenderedProbe, at_corpus_level, corpus_probes, probe_truth, render_probes

STEMS_SUFFIX: Final[str] = "-stems"
NOISE_KINDS: Final[Tuple[str, ...]] = ("white_noise", "walk_noise")
TONAL_CHANNELS: Final[List[ChannelName]] = ordered_channels(TONE_CHANNELS)
NOISE_CHANNELS: Final[List[ChannelName]] = [ChannelName.NOISE]
UNCLIPPED_GAIN: Final[float] = 1.0


def composite_stems(
    sample_rate: int,
    frame_rate: int,
    *,
    config: CorpusConfig,
    truth: TruthConfig,
) -> List[CorpusItem]:
    """The composite probes that mix a tone with noise, held as two stems: the tonal part and the noise.

    The tonal stem may take every tonal channel and the noise stem the noise channel, so the
    conversion is told which part is which and is left to match each. The parts are the composite's
    own layers from the corpus pass (see ``render_probes``), so the noise is the very draw the
    composite heard as one recording holds. They are brought to the corpus level and take the gain
    the composite's clipping applies to each sample, so they add up to the composite as it is heard.
    Being the same sound split, each carries the composite's truth.

    Args:
        sample_rate: The rate the parts are synthesized at.
        frame_rate: The frames per second a pitch line is written at.
        config: The probe corpus.
        truth: How a probe's pitch line counts its tone as sounding.

    Returns:
        List[CorpusItem]: One item per composite of both parts, in corpus order.
    """
    return [
        _composite(rendered, frame_rate, config, truth)
        for rendered in render_probes(sample_rate, config)
        if _holds_tone_and_noise(rendered.probe)
    ]


def composite_stems_catalog(config: CorpusConfig) -> Catalog:
    """Every category the composites held as stems fall in, beside its family."""
    return list(
        dict.fromkeys(
            (probe.family, _stems_category(probe)) for probe in corpus_probes(config) if _holds_tone_and_noise(probe)
        )
    )


def clip_gain(audio: np.ndarray) -> np.ndarray:
    """The gain clipping ``audio`` to full scale applies to each sample: ``clip(s) / s``, and 1 where ``s`` is 0.

    Parts of ``audio`` scaled by it add up to ``audio`` clipped, so a sound split into stems keeps the
    clipping the whole sound takes.
    """
    gain = np.full_like(audio, UNCLIPPED_GAIN)
    np.divide(clip_audio(audio), audio, out=gain, where=audio != 0.0)
    return gain


def _composite(rendered: RenderedProbe, frame_rate: int, config: CorpusConfig, truth: TruthConfig) -> CorpusItem:
    """The composite ``rendered`` held as its tonal part and its noise, as the corpus level hears them."""
    probe = rendered.probe
    gain = clip_gain(at_corpus_level(rendered.audio, config))
    parts = (rendered.part(_is_tonal), rendered.part(_is_noise))
    stems = StemsSources(
        sources=tuple((at_corpus_level(part, config) * gain).astype(np.float32) for part in parts),
        config=_two_stems(),
    )
    return CorpusItem(
        name=f"{probe.name}{STEMS_SUFFIX}",
        family=probe.family,
        category=_stems_category(probe),
        listed=True,
        audio=mixed(stems.sources),
        truth=probe_truth(rendered, frame_rate, truth),
        channels=stems.channels,
        stems=stems,
    )


def _stems_category(probe: Probe) -> str:
    """The category ``probe`` falls in once held as stems."""
    return f"{probe.category}{STEMS_SUFFIX}"


def _holds_tone_and_noise(probe: Probe) -> bool:
    """Whether ``probe`` is a composite holding both tonal layers and noise layers."""
    layers = probe.voice.layers
    return probe.family is Family.COMPOSITES and any(map(_is_tonal, layers)) and any(map(_is_noise, layers))


def _is_noise(layer: Layer) -> bool:
    """Whether ``layer`` is noise: its oscillator is one of ``NOISE_KINDS``."""
    return layer.oscillator.kind in NOISE_KINDS


def _is_tonal(layer: Layer) -> bool:
    """Whether ``layer`` is tonal: any layer other than noise."""
    return not _is_noise(layer)


def _two_stems() -> StemsConfig:
    """The composites' setup: the tonal part on every tonal channel and the noise on the noise channel."""
    return side_by_side([StemSettings.covering(TONAL_CHANNELS), StemSettings.covering(NOISE_CHANNELS)])
