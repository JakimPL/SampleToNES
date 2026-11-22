from typing import Final, FrozenSet, List

import numpy as np

from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.synthesis import build_corpus
from sampletones_tools.calibration.corpus.truth import LINE

from .conftest import FRAME_RATE

EXPECTED_CATEGORIES: Final[FrozenSet[str]] = frozenset(
    {"tone", "timbre", "noise", "mix", "transient", "dynamics", "polyphony"}
)


class TestBuildCorpus:
    def test_corpus_covers_every_category(self, corpus_items: List[CorpusItem]) -> None:
        assert {item.category for item in corpus_items} == EXPECTED_CATEGORIES

    def test_items_are_normalized_float32_of_uniform_length(
        self,
        corpus_items: List[CorpusItem],
        corpus_config: CorpusConfig,
        sample_rate: int,
    ) -> None:
        expected_length = int(corpus_config.item_seconds * sample_rate)
        for item in corpus_items:
            assert item.audio.dtype == np.float32
            assert item.audio.shape == (expected_length,)
            assert float(np.max(np.abs(item.audio))) <= 1.0

    def test_corpus_is_deterministic(self, corpus_config: CorpusConfig, sample_rate: int) -> None:
        first = build_corpus(sample_rate, FRAME_RATE, config=corpus_config)
        second = build_corpus(sample_rate, FRAME_RATE, config=corpus_config)
        assert [item.name for item in first] == [item.name for item in second]
        for item_a, item_b in zip(first, second):
            assert np.array_equal(item_a.audio, item_b.audio)

    def test_item_names_are_unique(self, corpus_items: List[CorpusItem]) -> None:
        names = [item.name for item in corpus_items]
        assert len(names) == len(set(names))


class TestPitchLines:
    def test_a_probe_holding_one_pitch_carries_it_through_every_frame(self, corpus_items: List[CorpusItem]) -> None:
        tone = next(item for item in corpus_items if item.category == "tone")

        assert tone.truth is not None
        assert len(set(tone.truth.pitches[LINE])) == 1

    def test_a_probe_of_no_steady_pitch_carries_no_truth(self, corpus_items: List[CorpusItem]) -> None:
        assert all(item.truth is None for item in corpus_items if item.category in ("noise", "polyphony"))
