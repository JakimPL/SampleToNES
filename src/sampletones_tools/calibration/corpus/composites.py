from typing import Final, List, Optional, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.synthesis.voice.layer import Layer
from sampletones_tools.synthesis.voice.voice import Voice

from .families import Family
from .item import CorpusItem, StemsSources
from .synthesis import PROBE_FAMILIES, Probe, corpus_probes

STEMS_SUFFIX: Final[str] = "-stems"
NOISE_KINDS: Final[Tuple[str, ...]] = ("white_noise", "walk_noise")
TONAL_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]
NOISE_CHANNELS: Final[List[ChannelName]] = [ChannelName.NOISE]


def composite_stems(sample_rate: int, *, config: CorpusConfig) -> List[CorpusItem]:
    """The composite probes that mix a tone with noise, held as two stems: the tonal part and the noise.

    The tonal stem may take every tonal channel and the noise stem the noise channel, so the
    conversion is told which part is which and is left to match each. Each part renders from the
    corpus seed of its own, which keeps every stem deterministic.

    Args:
        sample_rate: The rate the parts are synthesized at.
        config: The probe corpus.

    Returns:
        List[CorpusItem]: One item per composite of both parts, in corpus order.
    """
    items: List[CorpusItem] = []
    for probe in corpus_probes(config):
        parts = _parts(probe)
        if parts is None:
            continue

        sources = tuple(
            (
                config.amplitude * part.render(sample_rate=sample_rate, generator=np.random.default_rng(config.seed))
            ).astype(np.float32)
            for part in parts
        )
        items.append(
            CorpusItem(
                name=f"{probe.name}{STEMS_SUFFIX}",
                family=PROBE_FAMILIES[probe.category],
                category=f"{probe.category}{STEMS_SUFFIX}",
                listed=True,
                audio=np.sum(sources, axis=0).astype(np.float32),
                truth=None,
                channels=frozenset([*TONAL_CHANNELS, *NOISE_CHANNELS]),
                stems=StemsSources(sources=sources, config=_two_stems()),
            )
        )

    return items


def composite_stems_catalog(config: CorpusConfig) -> List[Tuple[Family, str]]:
    """Every category the composites held as stems fall in, beside its family."""
    return list(
        dict.fromkeys(
            (PROBE_FAMILIES[probe.category], f"{probe.category}{STEMS_SUFFIX}")
            for probe in corpus_probes(config)
            if _parts(probe) is not None
        )
    )


def _parts(probe: Probe) -> Optional[Tuple[Voice, Voice]]:
    """The probe's tonal layers and its noise layers as two voices, where it holds both."""
    if PROBE_FAMILIES[probe.category] is not Family.COMPOSITES:
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
    return StemsConfig(
        entries=(
            StemEntry(id=0, settings=StemSettings.covering(TONAL_CHANNELS)),
            StemEntry(id=1, settings=StemSettings.covering(NOISE_CHANNELS)),
        ),
        hierarchy=StemsHierarchy(levels=((0, 1),)),
    )
