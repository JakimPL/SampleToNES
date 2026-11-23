from typing import Final, List, Tuple

import pytest

from sampletones_core.constants.enums import SpectrumMethod
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.options import (
    categories_named,
    floats_named,
    levels_named,
    measured_categories,
    methods_named,
    settings_named,
)

KNOWN_CATEGORIES: Final[List[str]] = ["tone", "nes-pulse"]
KNOWN_SETTINGS: Final[List[str]] = ["greedy", "joint"]
CATALOG: Final[List[Tuple[Family, str]]] = [
    (Family.SINES, "tone"),
    (Family.SEQUENCES, "nes-pulse"),
    (Family.SEQUENCES, "nes-mix"),
]


class TestMethodsNamed:
    def test_nothing_named_is_the_default(self) -> None:
        assert methods_named(None, (SpectrumMethod.LOG_SPACED_FFT,)) == [SpectrumMethod.LOG_SPACED_FFT]

    def test_names_are_read_in_order(self) -> None:
        assert methods_named("cqt, fft", ()) == [SpectrumMethod.CQT, SpectrumMethod.FFT]

    def test_an_unknown_method_is_refused_with_the_known_ones(self) -> None:
        known = ", ".join(method.value for method in SpectrumMethod)

        with pytest.raises(ValueError, match=f"Unknown spectrum method 'dct'; the methods are {known}."):
            methods_named("fft,dct", ())


class TestFloatsNamed:
    def test_nothing_named_is_the_default(self) -> None:
        assert floats_named(None, (1.0,)) == [1.0]
        assert floats_named(None, ()) == []

    def test_values_are_read_in_order(self) -> None:
        assert floats_named("0.5, 1", ()) == [0.5, 1.0]

    def test_a_value_that_is_no_number_is_refused(self) -> None:
        with pytest.raises(ValueError, match="Not a number: 'high'"):
            floats_named("0.5,high", ())


class TestCategoriesNamed:
    def test_nothing_named_is_every_known_category(self) -> None:
        assert categories_named(None, KNOWN_CATEGORIES) == KNOWN_CATEGORIES

    def test_names_are_read_in_order(self) -> None:
        assert categories_named("nes-pulse, tone", KNOWN_CATEGORIES) == ["nes-pulse", "tone"]

    def test_an_unknown_category_is_refused_with_the_known_ones(self) -> None:
        with pytest.raises(ValueError, match="Unknown category 'chord'; the categories are tone, nes-pulse"):
            categories_named("tone,chord", KNOWN_CATEGORIES)


class TestSettingsNamed:
    def test_nothing_named_is_the_default(self) -> None:
        assert settings_named(None, ["joint"], KNOWN_SETTINGS) == ["joint"]

    def test_names_are_read_in_order(self) -> None:
        assert settings_named("joint,greedy", [], KNOWN_SETTINGS) == ["joint", "greedy"]

    def test_an_unknown_set_is_refused_with_the_known_ones(self) -> None:
        with pytest.raises(ValueError, match="Unknown set of settings 'gredy'; the sets are greedy, joint"):
            settings_named("gredy", [], KNOWN_SETTINGS)


class TestLevelsNamed:
    def test_nothing_named_is_the_default(self) -> None:
        assert levels_named(None, (VariantLevel.TRUE,)) == [VariantLevel.TRUE]

    def test_names_are_read_in_order(self) -> None:
        assert levels_named("true,default", ()) == [VariantLevel.TRUE, VariantLevel.DEFAULT]

    def test_an_unknown_level_is_refused_with_the_known_ones(self) -> None:
        known = ", ".join(level.value for level in VariantLevel)

        with pytest.raises(ValueError, match=f"Unknown level 'loud'; the levels are {known}."):
            levels_named("loud", ())


class TestMeasuredCategories:
    def test_nothing_named_or_skipped_measures_every_category_in_corpus_order(self) -> None:
        assert measured_categories(None, None, CATALOG) == ["tone", "nes-pulse", "nes-mix"]

    def test_a_skipped_family_leaves_out_every_category_it_holds(self) -> None:
        assert measured_categories(None, "sequences", CATALOG) == ["tone"]

    def test_a_skipped_category_leaves_out_that_category_alone(self) -> None:
        assert measured_categories(None, "nes-mix", CATALOG) == ["tone", "nes-pulse"]

    def test_a_skip_applies_to_the_categories_named_too(self) -> None:
        assert measured_categories("nes-mix,tone,nes-pulse", "nes-pulse", CATALOG) == ["nes-mix", "tone"]

    def test_a_name_that_is_neither_a_family_nor_a_category_is_refused(self) -> None:
        with pytest.raises(ValueError, match="Unknown family or category 'drums'; the names are sines, sequences, "):
            measured_categories(None, "drums", CATALOG)

    def test_skipping_everything_named_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no category to measure"):
            measured_categories("tone", "sines", CATALOG)
