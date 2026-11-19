from typing import List

import pytest

from sampletones_core.configs import Config
from sampletones_tools.calibration.corpus.families import FAMILY_ORDER
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.reference import reference_catalog, reference_categories, reference_corpus


@pytest.fixture(name="items", scope="module")
def items_fixture() -> List[CorpusItem]:
    return reference_corpus(Config(), reference_categories())


class TestReferenceCorpus:
    def test_every_category_the_corpus_holds_is_listed_in_corpus_order(self, items: List[CorpusItem]) -> None:
        assert reference_categories() == list(dict.fromkeys(item.category for item in items))

    def test_the_catalog_names_every_category_beside_its_family_in_corpus_order(self, items: List[CorpusItem]) -> None:
        assert reference_catalog() == list(dict.fromkeys((item.family, item.category) for item in items))

    def test_the_sounds_come_family_by_family(self, items: List[CorpusItem]) -> None:
        positions = [FAMILY_ORDER[item.family] for item in items]

        assert positions == sorted(positions)

    def test_a_run_of_a_few_categories_holds_those_alone(self) -> None:
        assert {item.category for item in reference_corpus(Config(), ["tone", "chords-two"])} == {"tone", "chords-two"}

    def test_names_stay_unique_across_the_synthesized_and_written_sounds(self, items: List[CorpusItem]) -> None:
        names = [item.name for item in items]

        assert len(names) == len(set(names))
