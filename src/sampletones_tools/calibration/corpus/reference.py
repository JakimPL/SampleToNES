from typing import List, Tuple

from sampletones_core.configs import Config
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.config.nes import NesCorpusConfig

from .families import FAMILY_ORDER, Family
from .item import CorpusItem
from .nes import build_nes_corpus
from .synthesis import PROBE_FAMILIES, build_corpus, corpus_probes


def reference_corpus(config: Config) -> List[CorpusItem]:
    """Every reference sound the package ships, family by family in the order a report presents them.

    Args:
        config: The configuration the run converts with, whose rates the sounds are made at.
    """
    items = [
        *build_corpus(config.library.sample_rate, config=CorpusConfig.load()),
        *build_nes_corpus(config, corpus=NesCorpusConfig.load()),
    ]
    return sorted(items, key=lambda item: FAMILY_ORDER[item.family])


def reference_catalog() -> List[Tuple[Family, str]]:
    """Every category the reference sounds fall in, beside its family, in the order the corpus holds them."""
    probed = [(PROBE_FAMILIES[category], category) for _, category, _ in corpus_probes(CorpusConfig.load())]
    written = [(Family.SEQUENCES, item.category) for item in NesCorpusConfig.load().items]
    ordered = sorted(dict.fromkeys([*probed, *written]), key=lambda entry: FAMILY_ORDER[entry[0]])
    return list(ordered)


def reference_categories() -> List[str]:
    """The categories of the reference sounds, in the order the corpus first holds each."""
    return [category for _, category in reference_catalog()]
