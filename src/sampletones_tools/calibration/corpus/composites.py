from typing import Final, List, Optional, Tuple

import numpy as np

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, ordered_channels
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.synthesis.voice.layer import Layer
from sampletones_tools.synthesis.voice.voice import Voice

from .families import Catalog, Family
from .item import CorpusItem, StemsSources
from .stems import mixed, side_by_side
from .synthesis import Probe, corpus_probes

STEMS_SUFFIX: Final[str] = "-stems"
NOISE_KINDS: Final[Tuple[str, ...]] = ("white_noise", "walk_noise")
TONAL_CHANNELS: Final[List[ChannelName]] = ordered_channels(TONE_CHANNELS)
NOISE_CHANNELS: Final[List[ChannelName]] = [ChannelName.NOISE]


def composite_stems(sample_rate: int, *, config: CorpusConfig) -> List[CorpusItem]:
    """The composite probes that mix a tone with noise, held as two stems: the tonal part and the noise.

    The tonal stem may take every tonal channel and the noise stem the noise channel, so the
    conversion is told which part is which and is left to match each. Each part renders from a
    generator of its own seeded with the corpus seed, which keeps every stem deterministic. The
    noise is therefore another draw than the one the composite heard as one recording holds.

    Args:
        sample_rate: The rate the parts are synthesized at.
        config: The probe corpus.

    Returns:
        List[CorpusItem]: One item per composite of both parts, in corpus order.
    """
    items: List[CorpusItem] = []
    for probe in corpus_probes(config):
        parts = _parts(probe)
        if parts is not None:
            items.append(_composite(probe, parts, sample_rate, config))

    return items


def composite_stems_catalog(config: CorpusConfig) -> Catalog:
    """Every category the composites held as stems fall in, beside its family."""
    return list(
        dict.fromkeys(
            (probe.family, _stems_category(probe)) for probe in corpus_probes(config) if _parts(probe) is not None
        )
    )


def _composite(probe: Probe, parts: Tuple[Voice, Voice], sample_rate: int, config: CorpusConfig) -> CorpusItem:
    """The composite ``probe`` held as its two ``parts``, each at the corpus amplitude."""
    stems = StemsSources(
        sources=tuple(_part_recording(part, sample_rate, config) for part in parts),
        config=_two_stems(),
    )
    return CorpusItem(
        name=f"{probe.name}{STEMS_SUFFIX}",
        family=probe.family,
        category=_stems_category(probe),
        listed=True,
        audio=mixed(stems.sources),
        truth=None,
        channels=stems.channels,
        stems=stems,
    )


def _part_recording(part: Voice, sample_rate: int, config: CorpusConfig) -> np.ndarray:
    """One part rendered from its own generator at the corpus seed, and scaled by the corpus amplitude."""
    rendered = part.render(sample_rate=sample_rate, generator=np.random.default_rng(config.seed))
    return (config.amplitude * rendered).astype(np.float32)


def _stems_category(probe: Probe) -> str:
    """The category ``probe`` falls in once held as stems."""
    return f"{probe.category}{STEMS_SUFFIX}"


def _parts(probe: Probe) -> Optional[Tuple[Voice, Voice]]:
    """The probe's tonal layers and its noise layers as two voices, where it is a composite holding both.

    A layer is noise where its oscillator is one of ``NOISE_KINDS``, and tonal otherwise.
    """
    if probe.family is not Family.COMPOSITES:
        return None

    tonal: List[Layer] = [layer for layer in probe.voice.layers if layer.oscillator.kind not in NOISE_KINDS]
    noisy: List[Layer] = [layer for layer in probe.voice.layers if layer.oscillator.kind in NOISE_KINDS]
    if not tonal or not noisy:
        return None

    return (
        probe.voice.model_copy(update={"layers": tuple(tonal)}),
        probe.voice.model_copy(update={"layers": tuple(noisy)}),
    )


def _two_stems() -> StemsConfig:
    """The composites' setup: the tonal part on every tonal channel and the noise on the noise channel."""
    return side_by_side([StemSettings.covering(TONAL_CHANNELS), StemSettings.covering(NOISE_CHANNELS)])
