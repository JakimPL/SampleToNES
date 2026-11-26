from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_core.configs.generation import (
    AssignmentConfig,
    ChannelInertia,
    DecoderConfig,
    GenerationConfig,
    WeightsConfig,
)
from sampletones_core.constants.enums import AssignmentMethod, ChannelName, SelectorName

KEPT: Final[float] = 0.5
FREE: Final[float] = 0.0


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


class TestInertiaKeepsTheNeighborPass:
    """Inertia keeps a frame's choice to its neighbors in the neighbor pass, so it runs with that pass."""

    def test_inertia_runs_with_the_neighbor_pass(self) -> None:
        assignment = AssignmentConfig(method=AssignmentMethod.JOINT, neighbors=1, inertia=ChannelInertia(triangle=0.5))

        assert GenerationConfig(assignment=assignment).assignment.inertia.of(ChannelName.TRIANGLE) == 0.5

    def test_inertia_without_the_neighbor_pass_is_refused(self) -> None:
        assignment = AssignmentConfig(
            method=AssignmentMethod.JOINT, neighbors=0, inertia=ChannelInertia(pulse1=0.0, noise=0.5)
        )

        with pytest.raises(ValidationError, match="neighbor pass"):
            GenerationConfig(assignment=assignment)

    def test_no_inertia_runs_without_the_neighbor_pass(self) -> None:
        free = ChannelInertia.model_validate({channel_name.value: FREE for channel_name in ChannelName.items()})
        assignment = AssignmentConfig(method=AssignmentMethod.JOINT, neighbors=0, inertia=free)

        assert not GenerationConfig(assignment=assignment).assignment.inertia.binding

    @pytest.mark.parametrize("channel_name", ChannelName.items())
    def test_any_one_channel_keeping_to_its_neighbors_binds(self, channel_name: ChannelName) -> None:
        inertia = ChannelInertia.model_validate(
            {other.value: KEPT if other == channel_name else FREE for other in ChannelName.items()}
        )

        assert inertia.binding

    def test_a_negative_inertia_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ChannelInertia(pulse1=-0.5)

    @pytest.mark.parametrize("channel_name", ChannelName.items())
    def test_each_channel_keeps_its_own_inertia(self, channel_name: ChannelName) -> None:
        inertia = ChannelInertia.model_validate(
            {other.value: 0.75 if other == channel_name else 0.0 for other in ChannelName.items()}
        )

        assert inertia.of(channel_name) == 0.75
        assert all(inertia.of(other) == 0.0 for other in ChannelName.items() if other != channel_name)


class TestTheBoundsOfTheSettings:
    def test_a_negative_count_of_neighbor_passes_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            AssignmentConfig(neighbors=-1)

    def test_a_negative_channel_price_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            WeightsConfig(channel_price=-0.01)


class TestADocumentWrittenBeforeTheLayers:
    """A reconstruction written before the spectrum layers existed reads the shipped layers as it loads."""

    def test_its_generation_holds_the_shipped_layers_and_hashes(self) -> None:
        shipped = GenerationConfig()
        data = GenerationConfig.unpack(shipped.serialize())
        data.pop("layers")

        older = GenerationConfig.deserialize_inner(data)

        assert older == shipped
        assert hash(older) == hash(shipped)
