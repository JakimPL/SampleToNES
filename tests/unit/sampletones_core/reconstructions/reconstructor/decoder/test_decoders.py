import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import SINGLE_STATE_LATTICE_WIDTH
from sampletones_core.constants.enums import ChannelName, SelectorName
from sampletones_core.reconstructions.reconstructor.decoder import DECODERS
from sampletones_core.reconstructions.reconstructor.decoder.base import ChannelLattice, Lattices
from sampletones_core.reconstructions.reconstructor.decoder.greedy import GreedyDecoder

from .conftest import JUMPED, STEADY, per_frame_best, state


class TestDecoderCatalog:
    def test_every_selector_name_is_answered(self) -> None:
        assert set(DECODERS) == set(SelectorName)

    @pytest.mark.parametrize("selector_name", list(SelectorName))
    def test_a_decoder_reads_at_least_one_candidate_per_frame(
        self,
        selector_name: SelectorName,
        config: Config,
    ) -> None:
        assert DECODERS[selector_name](config).lattice_width >= SINGLE_STATE_LATTICE_WIDTH


class TestDecodedShape:
    @staticmethod
    def _lattices() -> Lattices:
        return {
            ChannelName.PULSE1: [(state(STEADY, 0.1),), (state(STEADY, 0.2),)],
            ChannelName.TRIANGLE: [(state(STEADY, 0.3),), (state(STEADY, 0.4),)],
        }

    @pytest.mark.parametrize("selector_name", list(SelectorName))
    def test_every_channel_answers_each_of_its_frames(
        self,
        selector_name: SelectorName,
        config: Config,
    ) -> None:
        lattices = self._lattices()

        streams = DECODERS[selector_name](config).decode(lattices)

        assert set(streams) == set(lattices)
        assert {name: len(stream) for name, stream in streams.items()} == {
            name: len(frames) for name, frames in lattices.items()
        }

    @pytest.mark.parametrize("selector_name", list(SelectorName))
    def test_a_channel_with_no_frames_answers_nothing(
        self,
        selector_name: SelectorName,
        config: Config,
    ) -> None:
        assert DECODERS[selector_name](config).decode({ChannelName.PULSE1: []}) == {ChannelName.PULSE1: []}


class TestGreedyDecoder:
    def test_reads_one_candidate_per_frame(self, greedy_decoder: GreedyDecoder) -> None:
        assert greedy_decoder.lattice_width == SINGLE_STATE_LATTICE_WIDTH

    def test_plays_the_head_of_each_column(self, greedy_decoder: GreedyDecoder) -> None:
        """A column arrives best first, so its head is what the frame's own cost chose."""
        frames: ChannelLattice = [
            (state(STEADY, 0.00), state(JUMPED, 0.05)),
            (state(JUMPED, 0.00), state(STEADY, 0.05)),
        ]

        streams = greedy_decoder.decode({ChannelName.PULSE1: frames})

        assert [candidate.instruction for candidate in streams[ChannelName.PULSE1]] == per_frame_best(frames)
        assert [candidate.instruction for candidate in streams[ChannelName.PULSE1]] == [STEADY, JUMPED]
