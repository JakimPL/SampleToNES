from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exports.ceilings import (
    FORMAT_STORED_LENGTHS,
    FormatShortening,
    format_shortenings,
)
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.registry import build_tracker_backends
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.specification.macros import MAX_MACRO_LENGTH
from sampletones_core.formats.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SHORT_ENVELOPE: Final[int] = 16
PAST_A_SEQUENCE: Final[int] = 300
PAST_A_MACRO: Final[int] = 600


def items(count: int) -> Envelope[int]:
    return Envelope[int](items=(0,) * count)


class TestTheFormatsThatStoreADimension:
    def test_every_tracker_format_states_what_it_stores(self) -> None:
        assert set(FORMAT_STORED_LENGTHS) == set(build_tracker_backends())


class TestWhatEachFormatKeeps(BaseTestSuite):
    """Each format keeps as many items as its own specification bounds a dimension to."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        feature_key: FeatureKey
        item_count: int
        expected: Tuple[FormatShortening, ...]

    test_cases = (
        TestCase(
            feature_key=FeatureKey.VOLUME,
            item_count=SHORT_ENVELOPE,
            expected=(),
            label="short_volume",
        ),
        TestCase(
            feature_key=FeatureKey.VOLUME,
            item_count=PAST_A_SEQUENCE,
            expected=(FormatShortening(export_format=ExportFormat.FAMITRACKER, kept=MAX_SEQUENCE_ITEMS),),
            label="volume_past_a_sequence",
        ),
        TestCase(
            feature_key=FeatureKey.VOLUME,
            item_count=PAST_A_MACRO,
            expected=(
                FormatShortening(export_format=ExportFormat.FAMITRACKER, kept=MAX_SEQUENCE_ITEMS),
                FormatShortening(export_format=ExportFormat.BITPHASE, kept=MAX_MACRO_LENGTH),
                FormatShortening(export_format=ExportFormat.BITPHASE_PRESET, kept=MAX_MACRO_LENGTH),
            ),
            label="volume_past_a_macro",
        ),
        TestCase(
            feature_key=FeatureKey.ARPEGGIO,
            item_count=PAST_A_MACRO,
            expected=(
                FormatShortening(export_format=ExportFormat.FAMITRACKER, kept=MAX_SEQUENCE_ITEMS),
                FormatShortening(export_format=ExportFormat.BITPHASE_PRESET, kept=MAX_MACRO_LENGTH),
            ),
            label="arpeggio_past_a_macro",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_each_format_names_what_it_keeps(self, test_case: TestCase) -> None:
        assert format_shortenings(test_case.feature_key, items(test_case.item_count)) == test_case.expected
