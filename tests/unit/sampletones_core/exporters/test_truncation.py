from typing import Final, Optional

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.truncation import (
    EnvelopeTruncation,
    instrument_truncation,
    is_shortened,
)
from sampletones_core.features.envelope import Envelope

ITEM_LIMIT: Final[int] = 252
REFERENCE_PITCH: Final[int] = 60
LONG_VOLUME: Final[int] = 600
LONGER_DIMENSION: Final[int] = 700


def capped(feature_key: FeatureKey, envelope: Envelope[int]) -> int:
    """A format storing every dimension up to one limit."""
    return min(len(envelope.items), ITEM_LIMIT)


def contour_whole(feature_key: FeatureKey, envelope: Envelope[int]) -> int:
    """A format storing the contour whole and every other dimension up to one limit."""
    if feature_key is FeatureKey.ARPEGGIO:
        return len(envelope.items)

    return capped(feature_key, envelope)


def items(count: int) -> Envelope[int]:
    return Envelope[int](items=(0,) * count)


def build(
    volume: int,
    arpeggio: int,
    *,
    pitch: Optional[int] = None,
) -> Features:
    return Features(
        initial_pitch=REFERENCE_PITCH,
        volume=items(volume),
        arpeggio=items(arpeggio),
        pitch=None if pitch is None else items(pitch),
        hi_pitch=None,
        duty_cycle=None,
    )


class TestEnvelopeTruncationSummarize:
    def test_instruments_that_all_fit_report_nothing(self) -> None:
        assert EnvelopeTruncation.summarize([None, None]) is None

    def test_an_empty_export_reports_nothing(self) -> None:
        assert EnvelopeTruncation.summarize([]) is None

    def test_the_summary_spans_every_shortened_instrument(self) -> None:
        summary = EnvelopeTruncation.summarize(
            [
                None,
                EnvelopeTruncation(frames=ITEM_LIMIT, source_frames=300, instruments=1),
                EnvelopeTruncation(frames=ITEM_LIMIT, source_frames=480, instruments=1),
            ]
        )
        assert summary == EnvelopeTruncation(frames=ITEM_LIMIT, source_frames=480, instruments=2)


class TestWhetherAFormatShortensADimension:
    def test_a_dimension_the_format_stores_whole_is_kept(self) -> None:
        assert is_shortened(FeatureKey.VOLUME, items(ITEM_LIMIT), capped) is False

    def test_a_dimension_past_what_the_format_stores_is_shortened(self) -> None:
        assert is_shortened(FeatureKey.VOLUME, items(ITEM_LIMIT + 1), capped) is True

    def test_each_format_answers_by_its_own_length(self) -> None:
        contour = items(ITEM_LIMIT + 1)
        assert is_shortened(FeatureKey.ARPEGGIO, contour, capped) is True
        assert is_shortened(FeatureKey.ARPEGGIO, contour, contour_whole) is False


class TestWhatAnInstrumentReportsLeavingOut:
    def test_dimensions_within_what_the_format_stores_report_nothing(self) -> None:
        assert instrument_truncation(build(ITEM_LIMIT, ITEM_LIMIT), capped) is None

    def test_a_shortened_instrument_reports_both_counts(self) -> None:
        assert instrument_truncation(build(LONG_VOLUME, ITEM_LIMIT), capped) == EnvelopeTruncation(
            frames=ITEM_LIMIT,
            source_frames=LONG_VOLUME,
            instruments=1,
        )

    def test_the_longest_shortened_dimension_states_the_source(self) -> None:
        truncation = instrument_truncation(build(LONG_VOLUME, ITEM_LIMIT, pitch=LONGER_DIMENSION), capped)
        assert truncation is not None
        assert truncation.source_frames == LONGER_DIMENSION

    def test_a_dimension_a_format_holds_whole_leaves_the_report_to_the_others(self) -> None:
        """A contour stored whole is no part of what the format left out, however long it runs."""
        assert instrument_truncation(build(LONG_VOLUME, LONGER_DIMENSION), contour_whole) == EnvelopeTruncation(
            frames=ITEM_LIMIT,
            source_frames=LONG_VOLUME,
            instruments=1,
        )

    def test_a_long_dimension_the_format_holds_whole_reports_nothing(self) -> None:
        assert instrument_truncation(build(ITEM_LIMIT, LONGER_DIMENSION), contour_whole) is None
