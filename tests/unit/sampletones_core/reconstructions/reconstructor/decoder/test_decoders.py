from dataclasses import dataclass
from typing import Final, List, Tuple

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import SINGLE_STATE_LATTICE_WIDTH
from sampletones_core.constants.enums import ChannelName, SelectorName
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions.reconstructor.decoder import DECODERS
from sampletones_core.reconstructions.reconstructor.decoder.base import Alternatives, ChannelLattice, Lattices
from sampletones_core.reconstructions.reconstructor.decoder.greedy import GreedyDecoder
from sampletones_core.reconstructions.reconstructor.decoder.transition import TransitionWeights
from sampletones_core.reconstructions.reconstructor.matching import Column
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.continuity import ChannelContinuity
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .conftest import (
    JUMPED,
    RAISED,
    SEMITONE,
    STEADY,
    alone_in_a_stem,
    heads_pooled,
    per_frame_best,
    priced_by_the_semitone,
    state,
)

PATH_DECODERS: Final[Tuple[SelectorName, ...]] = (SelectorName.VITERBI, SelectorName.COMBINATIONS)
RECORDING_FRAMES: Final[int] = 3
BETWEEN_ONE_CHANGE_AND_TWO: Final[float] = 1.5 * SEMITONE
MORE_THAN_TWO_CHANGES: Final[float] = 2.5 * SEMITONE
HELD_INERTIA: Final[float] = 1.0


def _played(alternatives: Alternatives, selector: SelectorName, config: Config) -> List[InstructionUnion]:
    """What the pulse plays, decoded by ``selector`` charging ``SEMITONE`` a semitone."""
    streams = DECODERS[selector](priced_by_the_semitone(config)).decode(alternatives)
    return [candidate.instruction for candidate in streams[ChannelName.PULSE1]]


def _steady_but_at(frame: int, offered: Column) -> ChannelLattice:
    """A steady note in every frame of the recording, the column at ``frame`` offering ``offered``."""
    lattice: ChannelLattice = [(state(STEADY, 0.0),) for _ in range(RECORDING_FRAMES)]
    lattice[frame] = offered
    return lattice


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

        streams = DECODERS[selector_name](config).decode(heads_pooled(lattices))

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
        assert DECODERS[selector_name](config).decode(heads_pooled({ChannelName.PULSE1: []})) == {
            ChannelName.PULSE1: []
        }


class TestGreedyDecoder:
    def test_reads_one_candidate_per_frame(self, greedy_decoder: GreedyDecoder) -> None:
        assert greedy_decoder.lattice_width == SINGLE_STATE_LATTICE_WIDTH

    def test_plays_the_head_of_each_column(self, greedy_decoder: GreedyDecoder) -> None:
        """A column arrives best first, so its head is what the frame's own cost chose."""
        frames: ChannelLattice = [
            (state(STEADY, 0.00), state(JUMPED, 0.05)),
            (state(JUMPED, 0.00), state(STEADY, 0.05)),
        ]

        streams = greedy_decoder.decode(Alternatives(lattices={ChannelName.PULSE1: frames}, pools={}))

        assert [candidate.instruction for candidate in streams[ChannelName.PULSE1]] == per_frame_best(frames)
        assert [candidate.instruction for candidate in streams[ChannelName.PULSE1]] == [STEADY, JUMPED]


@pytest.mark.parametrize("selector", PATH_DECODERS, ids=[selector.value for selector in PATH_DECODERS])
class TestAPathOfOneChannel:
    """A path through one channel's frames, which the Viterbi and the combinations decoders read alike.

    A one-channel stem's combinations are its channel's candidates, so a move of the channel trades the
    frame's cost against its change under either decoder.
    """

    def test_a_recording_of_one_frame_plays_its_cheapest_alternative_wherever_it_stands(
        self, selector: SelectorName, config: Config
    ) -> None:
        lattice: ChannelLattice = [(state(STEADY, 0.2), state(RAISED, 0.1))]

        assert _played(alone_in_a_stem(lattice), selector, config) == [RAISED]

    def test_a_frame_offering_one_alternative_plays_it_whatever_it_costs(
        self, selector: SelectorName, config: Config
    ) -> None:
        """The second frame offers the octave alone, so the path jumps to it and holds it into the third."""
        lattice: ChannelLattice = [
            (state(STEADY, 0.0),),
            (state(JUMPED, 1.0),),
            (state(STEADY, 0.0), state(JUMPED, 0.0)),
        ]

        assert _played(alone_in_a_stem(lattice), selector, config) == [STEADY, JUMPED, JUMPED]


@pytest.mark.parametrize("selector", PATH_DECODERS, ids=[selector.value for selector in PATH_DECODERS])
class TestTheEdgesOfAPath(BaseTestSuite):
    """A frame at either end of a recording pays one change to move, and an inner frame one each side.

    The steady note's frame saves between one change and two by moving a semitone, so the first and
    the last frame move and an inner frame holds.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        frame: int
        moved: bool

    test_cases = (
        TestCase(label="the_first_frame", frame=0, moved=True),
        TestCase(label="an_inner_frame", frame=1, moved=False),
        TestCase(label="the_last_frame", frame=RECORDING_FRAMES - 1, moved=True),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_frame_moves_where_it_saves_more_than_the_changes_it_pays_for(
        self, test_case: TestCase, selector: SelectorName, config: Config
    ) -> None:
        offered = (state(STEADY, BETWEEN_ONE_CHANGE_AND_TWO), state(RAISED, 0.0))

        played = _played(alone_in_a_stem(_steady_but_at(test_case.frame, offered)), selector, config)

        assert played[test_case.frame] == (RAISED if test_case.moved else STEADY)
        assert [note for frame, note in enumerate(played) if frame != test_case.frame] == [STEADY] * (
            RECORDING_FRAMES - 1
        )


@pytest.mark.parametrize("selector", PATH_DECODERS, ids=[selector.value for selector in PATH_DECODERS])
class TestATieOnAPath(BaseTestSuite):
    """Where moving saves exactly the changes it pays for, the alternative listed first stands, either way round.

    The last frame pays one change to move and an inner frame two, so each saves exactly that. A tie
    at the last frame is the path's end, and a tie at an inner frame is a state's predecessor.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        frame: int
        saving: float
        first: PulseInstruction

    test_cases = (
        TestCase(label="the_last_frame_holding_first", frame=RECORDING_FRAMES - 1, saving=SEMITONE, first=STEADY),
        TestCase(label="the_last_frame_moving_first", frame=RECORDING_FRAMES - 1, saving=SEMITONE, first=RAISED),
        TestCase(label="an_inner_frame_holding_first", frame=1, saving=2 * SEMITONE, first=STEADY),
        TestCase(label="an_inner_frame_moving_first", frame=1, saving=2 * SEMITONE, first=RAISED),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_alternative_listed_first_takes_the_tie(
        self, test_case: TestCase, selector: SelectorName, config: Config
    ) -> None:
        holding, moving = state(STEADY, test_case.saving), state(RAISED, 0.0)
        offered = (holding, moving) if test_case.first == STEADY else (moving, holding)

        played = _played(alone_in_a_stem(_steady_but_at(test_case.frame, offered)), selector, config)

        assert played[test_case.frame] == test_case.first


@pytest.mark.parametrize("selector", PATH_DECODERS, ids=[selector.value for selector in PATH_DECODERS])
class TestTheChargeAPathReads(BaseTestSuite):
    """A charge the assignment adds to an alternative's cost weighs on the path beside the path's own changes.

    The neighbor pass charges an alternative ``inertia`` times its changes from the frames beside it,
    and the decoder charges the same changes again between frames. An inner frame saving more than
    its two changes moves at inertia zero, and holds once the charge doubles what moving costs.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        inertia: float
        moved: bool

    test_cases = (
        TestCase(label="at_inertia_zero", inertia=0.0, moved=True),
        TestCase(label="at_a_positive_inertia", inertia=HELD_INERTIA, moved=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_charged_move_pays_its_changes_twice(
        self, test_case: TestCase, selector: SelectorName, config: Config
    ) -> None:
        continuity = ChannelContinuity(
            before=STEADY,
            after=STEADY,
            weights=TransitionWeights.of(priced_by_the_semitone(config)),
            inertia=test_case.inertia,
        )
        offered = (state(STEADY, MORE_THAN_TWO_CHANGES), state(RAISED, continuity.charge(RAISED)))

        played = _played(alone_in_a_stem(_steady_but_at(1, offered)), selector, config)

        assert played[1] == (RAISED if test_case.moved else STEADY)
