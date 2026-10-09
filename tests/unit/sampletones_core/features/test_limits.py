from typing import Final, List, Optional, Sequence

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.features.limits import within_limit

LIMIT: Final[int] = 4
RELEASE: Final[int] = 0
SOUNDING_LEVEL: Final[int] = 8


def envelope(items: Sequence[int], loop_point: Optional[int] = None) -> Envelope[int]:
    return Envelope[int](items=tuple(items), loop_point=loop_point)


def released(length: int) -> List[int]:
    return [SOUNDING_LEVEL] * (length - 1) + [RELEASE]


def sounding(length: int) -> List[int]:
    return [SOUNDING_LEVEL] * length


class TestADimensionWithinTheLimit:
    def test_a_shorter_dimension_is_kept_whole(self) -> None:
        source = envelope(sounding(LIMIT - 1))
        assert within_limit(FeatureKey.VOLUME, source, LIMIT) == source

    def test_a_dimension_at_the_limit_is_kept_whole(self) -> None:
        source = envelope(released(LIMIT))
        assert within_limit(FeatureKey.VOLUME, source, LIMIT) == source

    def test_a_longer_dimension_keeps_its_opening_items(self) -> None:
        source = sounding(LIMIT + 3)
        assert within_limit(FeatureKey.ARPEGGIO, envelope(source), LIMIT).items == tuple(source[:LIMIT])

    def test_the_point_it_repeats_from_stays_within_what_is_kept(self) -> None:
        kept = within_limit(FeatureKey.ARPEGGIO, envelope(sounding(LIMIT + 3), loop_point=LIMIT + 1), LIMIT)
        assert kept.loop_point == LIMIT - 1


class TestTheReleaseAVolumeEndsOn:
    """A volume dimension ending at silence is what releases a note, so a format keeps that item.

    A dimension halting on its last item holds that value for as long as the note sounds, so a
    shortened volume that dropped its silence would sound on.
    """

    def test_a_released_dimension_past_the_limit_still_ends_at_its_release(self) -> None:
        kept = within_limit(FeatureKey.VOLUME, envelope(released(LIMIT + 1)), LIMIT)
        assert len(kept.items) == LIMIT
        assert kept.items[-1] == RELEASE

    def test_the_release_displaces_the_last_item_that_would_not_fit(self) -> None:
        source = released(LIMIT + 1)
        kept = within_limit(FeatureKey.VOLUME, envelope(source), LIMIT)
        assert kept.items == tuple(source[: LIMIT - 1]) + (RELEASE,)

    def test_a_dimension_that_goes_on_sounding_keeps_its_opening_items(self) -> None:
        source = sounding(LIMIT + 3)
        kept = within_limit(FeatureKey.VOLUME, envelope(source), LIMIT)
        assert kept.items == tuple(source[:LIMIT])

    def test_a_circling_dimension_reads_its_final_silence_as_part_of_the_cycle(self) -> None:
        source = released(LIMIT + 1)
        kept = within_limit(FeatureKey.VOLUME, envelope(source, loop_point=0), LIMIT)
        assert kept.items == tuple(source[:LIMIT])

    def test_a_dimension_other_than_volume_keeps_its_opening_items(self) -> None:
        source = released(LIMIT + 1)
        kept = within_limit(FeatureKey.ARPEGGIO, envelope(source), LIMIT)
        assert kept.items == tuple(source[:LIMIT])
