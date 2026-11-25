import math
from typing import Dict, Final, FrozenSet, List

import numpy as np
import pytest

from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.config.truth import TruthConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.synthesis import build_corpus
from sampletones_tools.calibration.corpus.truth import LINE, PitchLine

from .conftest import FRAME_RATE

EXPECTED_CATEGORIES: Final[FrozenSet[str]] = frozenset(
    {"tone", "timbre", "noise", "mix", "transient", "dynamics", "polyphony"}
)
FRACTIONAL_SECONDS: Final[float] = 0.75


@pytest.fixture(name="by_name", scope="module")
def by_name_fixture(corpus_items: List[CorpusItem]) -> Dict[str, CorpusItem]:
    return {item.name: item for item in corpus_items}


@pytest.fixture(name="audible_floor", scope="module")
def audible_floor_fixture(truth_config: TruthConfig) -> float:
    return truth_config.audible_floor


def _line(item: CorpusItem) -> PitchLine:
    assert item.truth is not None
    return item.truth.pitches[LINE]


def _middle(frame: int) -> float:
    return (frame + 0.5) / FRAME_RATE


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

    def test_corpus_is_deterministic(
        self, corpus_config: CorpusConfig, truth_config: TruthConfig, sample_rate: int
    ) -> None:
        first = build_corpus(sample_rate, FRAME_RATE, config=corpus_config, truth=truth_config)
        second = build_corpus(sample_rate, FRAME_RATE, config=corpus_config, truth=truth_config)
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

    def test_a_tone_under_noise_carries_its_pitch_through_every_frame(
        self, by_name: Dict[str, CorpusItem], corpus_config: CorpusConfig
    ) -> None:
        under_hiss = [f"mix-noise{level:g}" for level in corpus_config.mix.noise_levels]

        for name in under_hiss:
            assert set(_line(by_name[name])) == {corpus_config.reference_frequency}
        assert set(_line(by_name["mix-bass-hi-hats"])) == {corpus_config.mix.bass_frequency}

    def test_the_pluck_holds_its_pitch_until_its_decay_falls_below_the_audible_range(
        self, by_name: Dict[str, CorpusItem], corpus_config: CorpusConfig, audible_floor: float
    ) -> None:
        line = _line(by_name["transient-pluck"])
        heard_until = -corpus_config.transient.attack_tone_decay_seconds * math.log(audible_floor)
        heard = [_middle(frame) <= heard_until for frame in range(len(line))]

        assert any(heard) and not all(heard)
        assert line == tuple(corpus_config.reference_frequency if sounding else None for sounding in heard)

    def test_the_crescendo_holds_its_pitch_from_where_it_rises_into_the_audible_range(
        self, by_name: Dict[str, CorpusItem], corpus_config: CorpusConfig, audible_floor: float
    ) -> None:
        line = _line(by_name["dynamics-crescendo"])
        heard_from = audible_floor * corpus_config.item_seconds
        heard = [_middle(frame) >= heard_from for frame in range(len(line))]

        assert any(heard) and not all(heard)
        assert line == tuple(corpus_config.reference_frequency if sounding else None for sounding in heard)

    def test_a_line_covers_every_frame_the_audio_reaches(
        self, corpus_config: CorpusConfig, truth_config: TruthConfig, sample_rate: int
    ) -> None:
        config = corpus_config.model_copy(update={"item_seconds": FRACTIONAL_SECONDS})

        for item in build_corpus(sample_rate, FRAME_RATE, config=config, truth=truth_config):
            if item.truth is not None:
                assert len(_line(item)) == math.ceil(len(item.audio) * FRAME_RATE / sample_rate)
