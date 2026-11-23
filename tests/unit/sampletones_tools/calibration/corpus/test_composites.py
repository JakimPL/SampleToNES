from dataclasses import dataclass
from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.config.truth import TruthConfig
from sampletones_tools.calibration.corpus.composites import (
    STEMS_SUFFIX,
    clip_gain,
    composite_stems,
    composite_stems_catalog,
)
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.synthesis import build_corpus
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .conftest import FRAME_RATE, SAMPLE_RATE

FULL_SCALE: Final[float] = 1.0
LOUDEST_AMPLITUDE: Final[float] = 1.0
FLOAT32_TOLERANCE: Final[float] = 1e-6


@pytest.fixture(name="composites", scope="module")
def composites_fixture() -> List[CorpusItem]:
    return _twins(CorpusConfig.load())


@pytest.fixture(name="by_name", scope="module")
def by_name_fixture(composites: List[CorpusItem]) -> Dict[str, CorpusItem]:
    return {item.name: item for item in composites}


@pytest.fixture(name="loud_config", scope="module")
def loud_config_fixture() -> CorpusConfig:
    return CorpusConfig.load().model_copy(update={"amplitude": LOUDEST_AMPLITUDE})


def _twins(config: CorpusConfig) -> List[CorpusItem]:
    return composite_stems(SAMPLE_RATE, FRAME_RATE, config=config, truth=TruthConfig.load())


def _heard_as_one(config: CorpusConfig) -> Dict[str, CorpusItem]:
    items = build_corpus(SAMPLE_RATE, FRAME_RATE, config=config, truth=TruthConfig.load())
    return {item.name: item for item in items}


def _assert_adding_up_to_their_composites(twins: List[CorpusItem], composites: Dict[str, CorpusItem]) -> None:
    assert twins
    for twin in twins:
        assert twin.stems is not None
        composite = composites[twin.name.removesuffix(STEMS_SUFFIX)]
        np.testing.assert_allclose(sum(twin.stems.sources), composite.audio, atol=FLOAT32_TOLERANCE)
        np.testing.assert_allclose(twin.audio, composite.audio, atol=FLOAT32_TOLERANCE)


class TestTwins:
    def test_each_twin_s_stems_add_up_to_its_composite_heard_as_one(
        self, composites: List[CorpusItem], corpus_items: List[CorpusItem]
    ) -> None:
        _assert_adding_up_to_their_composites(composites, {item.name: item for item in corpus_items})

    def test_each_twin_carries_its_composite_s_truth(
        self, composites: List[CorpusItem], corpus_items: List[CorpusItem]
    ) -> None:
        heard_as_one = {item.name: item for item in corpus_items}

        assert any(twin.truth is not None for twin in composites)
        for twin in composites:
            assert twin.truth == heard_as_one[twin.name.removesuffix(STEMS_SUFFIX)].truth

    def test_a_clipped_composite_s_stems_add_up_to_it_clipped(self, loud_config: CorpusConfig) -> None:
        composites = _heard_as_one(loud_config)
        twins = _twins(loud_config)

        assert any(
            np.max(np.abs(composites[twin.name.removesuffix(STEMS_SUFFIX)].audio)) == FULL_SCALE for twin in twins
        )
        _assert_adding_up_to_their_composites(twins, composites)

    def test_the_stems_of_a_clipped_composite_mix_within_full_scale(self, loud_config: CorpusConfig) -> None:
        for twin in _twins(loud_config):
            assert twin.stems is not None
            assert float(np.max(np.abs(sum(twin.stems.sources)))) <= FULL_SCALE + FLOAT32_TOLERANCE


class TestClipGain(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        sample: float

    test_cases = (
        TestCase(sample=0.0, expected=1.0, label="silence"),
        TestCase(sample=0.5, expected=1.0, label="within full scale"),
        TestCase(sample=-1.0, expected=1.0, label="at full scale"),
        TestCase(sample=2.0, expected=0.5, label="past full scale"),
        TestCase(sample=-4.0, expected=0.25, label="past full scale below"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_sample_takes_the_gain_its_clipping_applies(self, test_case: TestCase) -> None:
        assert clip_gain(np.array([test_case.sample]))[0] == test_case.expected


class TestCompositeStems:
    def test_a_composite_of_a_tone_and_noise_is_held_as_two_stems_adding_up_to_it(
        self, composites: List[CorpusItem]
    ) -> None:
        assert composites
        for item in composites:
            assert item.family is Family.COMPOSITES and item.category.endswith(STEMS_SUFFIX)
            assert item.stems is not None and len(item.stems.sources) == 2
            np.testing.assert_allclose(sum(item.stems.sources), item.audio, atol=FLOAT32_TOLERANCE)

    def test_a_composite_of_tones_alone_has_no_stems_copy(self, by_name: Dict[str, CorpusItem]) -> None:
        assert f"polyphony-chord{STEMS_SUFFIX}" not in by_name
        assert f"polyphony-melody-snare{STEMS_SUFFIX}" in by_name

    def test_a_sound_of_noise_alone_is_no_composite(self, by_name: Dict[str, CorpusItem]) -> None:
        assert not any(name.startswith("noise-") for name in by_name)

    def test_the_tone_takes_the_tonal_channels_and_the_noise_the_noise_channel(
        self, composites: List[CorpusItem]
    ) -> None:
        for item in composites:
            assert item.stems is not None
            tonal, noise = (entry.settings.channel_set for entry in item.stems.config.entries)
            assert (tonal, noise) == (TONE_CHANNELS, frozenset({ChannelName.NOISE}))
            assert item.channels == frozenset(ChannelName.items())

    def test_the_catalog_names_the_categories_the_composites_fall_in(self, composites: List[CorpusItem]) -> None:
        assert composite_stems_catalog(CorpusConfig.load()) == list(
            dict.fromkeys((item.family, item.category) for item in composites)
        )
