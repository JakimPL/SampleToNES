from typing import List

import numpy as np
import pytest

from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.corpus.composites import STEMS_SUFFIX, composite_stems, composite_stems_catalog
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem

from .conftest import SAMPLE_RATE


@pytest.fixture(name="composites", scope="module")
def composites_fixture() -> List[CorpusItem]:
    return composite_stems(SAMPLE_RATE, config=CorpusConfig.load())


class TestCompositeStems:
    def test_a_composite_of_a_tone_and_noise_is_held_as_two_stems_adding_up_to_it(
        self, composites: List[CorpusItem]
    ) -> None:
        assert composites
        for item in composites:
            assert item.family is Family.COMPOSITES and item.category.endswith(STEMS_SUFFIX)
            assert item.stems is not None and len(item.stems.sources) == 2
            np.testing.assert_allclose(sum(item.stems.sources), item.audio, atol=1e-6)

    def test_the_catalog_names_the_categories_the_composites_fall_in(self, composites: List[CorpusItem]) -> None:
        assert composite_stems_catalog(CorpusConfig.load()) == list(
            dict.fromkeys((item.family, item.category) for item in composites)
        )
