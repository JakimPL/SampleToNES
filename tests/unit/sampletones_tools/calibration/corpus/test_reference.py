from typing import List

import pytest

from sampletones_core.configs import Config
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.reference import reference_categories, reference_corpus


@pytest.fixture(name="items", scope="module")
def items_fixture() -> List[CorpusItem]:
    return reference_corpus(Config())


class TestReferenceCorpus:
    def test_every_category_the_corpus_holds_is_listed_in_corpus_order(self, items: List[CorpusItem]) -> None:
        assert reference_categories() == list(dict.fromkeys(item.category for item in items))

    def test_names_stay_unique_across_the_synthesized_and_written_sounds(self, items: List[CorpusItem]) -> None:
        names = [item.name for item in items]

        assert len(names) == len(set(names))
