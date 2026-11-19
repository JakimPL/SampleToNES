from typing import List

from sampletones_core.configs import Config
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.config.nes import NesCorpusConfig

from .item import CorpusItem
from .nes import build_nes_corpus
from .synthesis import build_corpus, corpus_probes


def reference_corpus(config: Config) -> List[CorpusItem]:
    """Every reference sound the package ships: the synthesized probes, then the sounds written as NES frames.

    Args:
        config: The configuration the run converts with, whose rates the sounds are made at.
    """
    return [
        *build_corpus(config.library.sample_rate, config=CorpusConfig.load()),
        *build_nes_corpus(config, corpus=NesCorpusConfig.load()),
    ]


def reference_categories() -> List[str]:
    """The categories of the reference sounds, in the order the corpus first holds each."""
    probed = [category for _, category, _ in corpus_probes(CorpusConfig.load())]
    written = [item.category for item in NesCorpusConfig.load().items]
    return list(dict.fromkeys([*probed, *written]))
