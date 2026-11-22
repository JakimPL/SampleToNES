from typing import Dict, List

import numpy as np
import pytest

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.corpus.composites import STEMS_SUFFIX, composite_stems, composite_stems_catalog
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem

from .conftest import SAMPLE_RATE


@pytest.fixture(name="composites", scope="module")
def composites_fixture() -> List[CorpusItem]:
    return composite_stems(SAMPLE_RATE, config=CorpusConfig.load())


@pytest.fixture(name="by_name", scope="module")
def by_name_fixture(composites: List[CorpusItem]) -> Dict[str, CorpusItem]:
    return {item.name: item for item in composites}


class TestCompositeStems:
    def test_a_composite_of_a_tone_and_noise_is_held_as_two_stems_adding_up_to_it(
        self, composites: List[CorpusItem]
    ) -> None:
        assert composites
        for item in composites:
            assert item.family is Family.COMPOSITES and item.category.endswith(STEMS_SUFFIX)
            assert item.stems is not None and len(item.stems.sources) == 2
            np.testing.assert_allclose(sum(item.stems.sources), item.audio, atol=1e-6)

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
