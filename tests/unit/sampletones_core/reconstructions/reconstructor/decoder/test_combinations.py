from typing import Final, List, Sequence, Tuple

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions.reconstructor.decoder.base import (
    Alternatives,
    ChannelLattice,
    Lattices,
    Pool,
    StemPools,
    Streams,
)

from .conftest import JUMPED, STEADY, combination, combinations_decoder

PULSES: Final[Tuple[ChannelName, ChannelName]] = (ChannelName.PULSE1, ChannelName.PULSE2)
NEIGHBOR: Final[PulseInstruction] = PulseInstruction(on=True, pitch=STEADY.pitch + 1, volume=10, duty_cycle=0)
HELD: Final[Tuple[PulseInstruction, PulseInstruction]] = (STEADY, JUMPED)
UNISON: Final[Tuple[PulseInstruction, PulseInstruction]] = (STEADY, STEADY)
SWAPPED: Final[Tuple[PulseInstruction, PulseInstruction]] = (JUMPED, STEADY)


def _alternatives(channel_names: Tuple[ChannelName, ...], frames: List[Pool]) -> Alternatives:
    """One stem holding ``channel_names``, pooling ``frames``, each channel's column its head of every frame."""
    lattices: Lattices = {
        channel_name: [(pool[0].candidates[position],) for pool in frames]
        for position, channel_name in enumerate(channel_names)
    }
    return Alternatives(
        lattices=lattices,
        pools={0: StemPools(channel_names=channel_names, frames=frames)},
    )


def _played(streams: Streams, channel_name: ChannelName) -> List[InstructionUnion]:
    return [candidate.instruction for candidate in streams[channel_name]]


def _cheapest(frames: Sequence[Pool]) -> List[Tuple[InstructionUnion, ...]]:
    return [
        tuple(candidate.instruction for candidate in min(pool, key=lambda pooled: pooled.cost).candidates)
        for pool in frames
    ]


@pytest.fixture(name="flipping_frames")
def flipping_frames_fixture() -> List[Pool]:
    """Three frames whose cheapest combination moves the second pulse onto the first's note and back."""
    return [
        (combination(HELD, 0.00), combination(UNISON, 0.05)),
        (combination(UNISON, 0.00), combination(HELD, 0.05)),
        (combination(HELD, 0.00), combination(UNISON, 0.05)),
    ]


class TestCombinationsContinuity:
    def test_a_path_holds_the_whole_combination_where_the_cheapest_of_each_frame_flips_a_pulse(
        self,
        config: Config,
        flipping_frames: List[Pool],
    ) -> None:
        decoder = combinations_decoder(config, pitch_weight=1.0)

        streams = decoder.decode(_alternatives(PULSES, flipping_frames))

        assert len(set(_cheapest(flipping_frames))) > 1
        assert _played(streams, ChannelName.PULSE1) == [STEADY] * len(flipping_frames)
        assert _played(streams, ChannelName.PULSE2) == [JUMPED] * len(flipping_frames)

    def test_zero_transition_weights_play_the_cheapest_combination_of_each_frame(
        self,
        config: Config,
        flipping_frames: List[Pool],
    ) -> None:
        decoder = combinations_decoder(
            config, pitch_weight=0.0, volume_weight=0.0, timbre_weight=0.0, on_off_weight=0.0
        )

        streams = decoder.decode(_alternatives(PULSES, flipping_frames))

        played = list(zip(_played(streams, ChannelName.PULSE1), _played(streams, ChannelName.PULSE2)))
        assert played == _cheapest(flipping_frames)

    def test_either_order_of_the_pulses_lets_each_keep_its_note(self, config: Config) -> None:
        """A pooled combination stands in both orders of its pulses, so the path keeps each line on its channel."""
        frames: List[Pool] = [
            (combination(HELD, 0.0),),
            (combination(SWAPPED, 0.0), combination(HELD, 0.0)),
            (combination(SWAPPED, 0.0), combination(HELD, 0.0)),
        ]

        streams = combinations_decoder(config, pitch_weight=1.0).decode(_alternatives(PULSES, frames))

        assert _played(streams, ChannelName.PULSE1) == [STEADY] * len(frames)
        assert _played(streams, ChannelName.PULSE2) == [JUMPED] * len(frames)

    @pytest.mark.parametrize("saving, moved", [(0.1, False), (0.2, True)], ids=["saves less", "saves more"])
    def test_a_move_pays_where_the_frame_saves_more_than_the_change_costs(
        self,
        config: Config,
        saving: float,
        moved: bool,
    ) -> None:
        """A semitone costs 0.15, so a frame saving 0.2 by it moves and one saving 0.1 holds."""
        frames: List[Pool] = [
            (combination([STEADY], 0.0),),
            (combination([STEADY], saving), combination([NEIGHBOR], 0.0)),
        ]
        decoder = combinations_decoder(
            config, pitch_weight=0.15, volume_weight=0.0, timbre_weight=0.0, on_off_weight=0.0
        )

        streams = decoder.decode(_alternatives((ChannelName.PULSE1,), frames))

        assert _played(streams, ChannelName.PULSE1)[-1] == (NEIGHBOR if moved else STEADY)


class TestCombinationsCoverage:
    def test_reads_as_many_candidates_per_column_as_the_configured_shortlist(self, config: Config) -> None:
        assert combinations_decoder(config).lattice_width == config.generation.decoder.top_k

    def test_a_channel_in_no_stem_s_pools_is_refused(self, config: Config) -> None:
        frames: ChannelLattice = [(combination([STEADY], 0.0).candidates[0],)]

        with pytest.raises(ValueError, match="pools"):
            combinations_decoder(config).decode(Alternatives(lattices={ChannelName.PULSE1: frames}, pools={}))

    def test_every_stem_follows_a_path_of_its_own(self, config: Config, flipping_frames: List[Pool]) -> None:
        bass: List[Pool] = [(combination([NEIGHBOR], 0.0),) for _ in flipping_frames]
        lead = _alternatives(PULSES, flipping_frames)
        alternatives = Alternatives(
            lattices={**lead.lattices, ChannelName.TRIANGLE: [(pool[0].candidates[0],) for pool in bass]},
            pools={
                **lead.pools,
                1: StemPools(channel_names=(ChannelName.TRIANGLE,), frames=bass),
            },
        )

        streams = combinations_decoder(config, pitch_weight=1.0).decode(alternatives)

        assert list(streams) == list(alternatives.lattices)
        assert _played(streams, ChannelName.PULSE2) == [JUMPED] * len(flipping_frames)
        assert _played(streams, ChannelName.TRIANGLE) == [NEIGHBOR] * len(bass)
