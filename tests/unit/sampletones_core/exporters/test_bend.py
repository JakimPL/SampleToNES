from typing import Final, Optional, Sequence

from sampletones_core.constants.general import HI_PITCH_FACTOR
from sampletones_core.exporters.bend import bend_envelope
from sampletones_core.features.envelope import Envelope

FINE_STEPS: Final[Sequence[int]] = (0, -3, -7)
COARSE_STEPS: Final[Sequence[int]] = (0, 1, 2)


def envelope(items: Sequence[int], loop_point: Optional[int] = None) -> Envelope[int]:
    return Envelope[int](items=tuple(items), loop_point=loop_point)


class TestTheOffsetTwoDimensionsStateTogether:
    def test_a_fine_dimension_alone_carries_its_steps(self) -> None:
        assert bend_envelope(envelope(FINE_STEPS), None).items == tuple(FINE_STEPS)

    def test_a_coarse_step_counts_sixteen(self) -> None:
        assert bend_envelope(None, envelope(COARSE_STEPS)).items == tuple(
            step * HI_PITCH_FACTOR for step in COARSE_STEPS
        )

    def test_both_dimensions_reach_the_same_tick(self) -> None:
        combined = bend_envelope(envelope(FINE_STEPS), envelope(COARSE_STEPS))
        assert combined.items == tuple(
            fine + coarse * HI_PITCH_FACTOR for fine, coarse in zip(FINE_STEPS, COARSE_STEPS)
        )

    def test_a_channel_offering_neither_dimension_states_nothing(self) -> None:
        assert bend_envelope(None, None).items == ()

    def test_a_dimension_writing_no_items_states_nothing(self) -> None:
        assert bend_envelope(envelope(()), envelope(())).items == ()


class TestDimensionsOfDifferentLengths:
    def test_the_pair_runs_as_long_as_the_longer_of_them(self) -> None:
        combined = bend_envelope(envelope((1, 2, 3, 4)), envelope((1,)))
        assert len(combined.items) == 4

    def test_a_dimension_past_its_end_reads_at_the_value_it_holds(self) -> None:
        combined = bend_envelope(envelope((0, 0, 0)), envelope((1,)))
        assert combined.items == (HI_PITCH_FACTOR,) * 3

    def test_a_circling_dimension_reads_at_the_value_it_comes_round_to(self) -> None:
        combined = bend_envelope(envelope((1, 2), loop_point=0), envelope(()))
        assert combined.items == (1, 2)


class TestThePointThePairCirclesFrom:
    def test_a_pair_holding_its_last_value_states_no_point(self) -> None:
        assert bend_envelope(envelope(FINE_STEPS), envelope(COARSE_STEPS)).loop_point is None

    def test_the_earliest_point_either_dimension_states_carries(self) -> None:
        combined = bend_envelope(envelope((1, 2, 3), loop_point=2), envelope((0, 0, 0), loop_point=1))
        assert combined.loop_point == 1
