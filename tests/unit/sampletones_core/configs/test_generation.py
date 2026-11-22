import pytest
from pydantic import ValidationError

from sampletones_core.configs.generation import AssignmentConfig, DecoderConfig, GenerationConfig
from sampletones_core.constants.enums import AssignmentMethod, SelectorName


class TestTheDecoderReadsWhatTheAssignmentOffers:
    """The combinations decoder reads the pools only the joint assignment offers."""

    def test_the_combinations_decoder_runs_with_the_joint_assignment(self) -> None:
        generation = GenerationConfig(
            assignment=AssignmentConfig(method=AssignmentMethod.JOINT),
            decoder=DecoderConfig(selector=SelectorName.COMBINATIONS),
        )

        assert generation.decoder.selector == SelectorName.COMBINATIONS

    def test_the_combinations_decoder_with_picks_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="joint assignment"):
            GenerationConfig(
                assignment=AssignmentConfig(method=AssignmentMethod.PICKS),
                decoder=DecoderConfig(selector=SelectorName.COMBINATIONS),
            )

    @pytest.mark.parametrize("selector", [SelectorName.GREEDY, SelectorName.VITERBI], ids=["greedy", "viterbi"])
    @pytest.mark.parametrize("method", list(AssignmentMethod), ids=[method.value for method in AssignmentMethod])
    def test_a_decoder_of_one_channel_at_a_time_runs_with_either_assignment(
        self, selector: SelectorName, method: AssignmentMethod
    ) -> None:
        generation = GenerationConfig(
            assignment=AssignmentConfig(method=method), decoder=DecoderConfig(selector=selector)
        )

        assert (generation.assignment.method, generation.decoder.selector) == (method, selector)


class TestFramesHeardAmongTheirNeighbors:
    """A frame is assigned again among its neighbors by the joint assignment alone."""

    def test_the_joint_assignment_hears_its_neighbors(self) -> None:
        assignment = AssignmentConfig(method=AssignmentMethod.JOINT, neighbors=2)

        assert GenerationConfig(assignment=assignment).assignment.neighbors == 2

    def test_picks_heard_among_neighbors_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="joint assignment"):
            GenerationConfig(assignment=AssignmentConfig(method=AssignmentMethod.PICKS, neighbors=1))
