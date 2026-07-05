from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np

from sampletones_core.calibration.corpus import (
    CORPUS_ITEM_SECONDS,
    build_corpus,
    write_corpus,
)

SAMPLE_RATE: Final[int] = 22050
EXPECTED_CATEGORIES: Final[frozenset[str]] = frozenset({"tone", "timbre", "noise", "mix", "transient", "dynamics"})


class TestBuildCorpus:
    def test_corpus_covers_every_category(self) -> None:
        items = build_corpus(SAMPLE_RATE)
        assert {item.category for item in items} == EXPECTED_CATEGORIES

    def test_items_are_normalized_float32_of_uniform_length(self) -> None:
        expected_length = int(CORPUS_ITEM_SECONDS * SAMPLE_RATE)
        for item in build_corpus(SAMPLE_RATE):
            assert item.audio.dtype == np.float32
            assert item.audio.shape == (expected_length,)
            assert float(np.max(np.abs(item.audio))) <= 1.0

    def test_corpus_is_deterministic(self) -> None:
        first = build_corpus(SAMPLE_RATE)
        second = build_corpus(SAMPLE_RATE)
        assert [item.name for item in first] == [item.name for item in second]
        for item_a, item_b in zip(first, second):
            assert np.array_equal(item_a.audio, item_b.audio)

    def test_item_names_are_unique(self) -> None:
        names = [item.name for item in build_corpus(SAMPLE_RATE)]
        assert len(names) == len(set(names))


class TestWriteCorpus:
    def test_writes_one_wav_per_item(self, tmp_path: Path) -> None:
        items = build_corpus(SAMPLE_RATE)
        paths = write_corpus(items, tmp_path / "corpus", SAMPLE_RATE)
        assert set(paths) == {item.name for item in items}
        for path in paths.values():
            assert path.exists()
            assert path.suffix == ".wav"
