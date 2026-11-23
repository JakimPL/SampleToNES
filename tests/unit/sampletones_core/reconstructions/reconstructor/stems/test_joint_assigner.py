import itertools
from dataclasses import replace
from typing import Dict, Final, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_FRAME_COST
from sampletones_core.constants.enums import (
    ChannelName,
    GeneratorClassName,
    HierarchyMode,
    bending_channels,
)
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TonalInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.decoder.base import PooledCombination
from sampletones_core.reconstructions.reconstructor.decoder.transition import TransitionWeights
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import (
    UNVOICED_DISTANCE,
    JointAssigner,
    PulseHandover,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.choice import ScoredCombination
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.combinations import Rows
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.continuity import ChannelContinuity
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import separate_layouts
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
from sampletones_core.reconstructions.reconstructor.stems.models.pool import StemPool
from sampletones_core.reconstructions.reconstructor.window.profiles import frame_profiles
from sampletones_core.reconstructions.reconstructor.window.surroundings import (
    ChannelLine,
    TonalSurroundings,
    surroundings,
)
from tests.suite.base import BaseTestSuite

from ..conftest import rendered_fragment
from .conftest import decoded_lines, played_lines

LATTICE_WIDTH: Final[int] = 8
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: LEAD,
    ChannelName.PULSE2: HARMONY,
    ChannelName.TRIANGLE: BASS,
}
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
NEXT_CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: PulseInstruction(on=True, pitch=62, volume=12, duty_cycle=2),
    ChannelName.PULSE2: PulseInstruction(on=True, pitch=65, volume=8, duty_cycle=1),
    ChannelName.TRIANGLE: TriangleInstruction(on=True, pitch=45),
}


def _one_stem(channels: List[ChannelName], channel_cap: int) -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=0,
                settings=StemSettings(channels=channels, bends=bending_channels(channels), channel_cap=channel_cap),
            )
        ],
        hierarchy=StemsHierarchy(levels=[[0]], mode=HierarchyMode.ROUND_ROBIN),
    )


def _assigner(
    stems: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
) -> JointAssigner:
    return JointAssigner(stems, channels, matcher, LATTICE_WIDTH)


def _heads(assignment: StemFrameAssignment) -> Dict[ChannelName, InstructionUnion]:
    return {choice.channel_name: choice.instruction for choice in assignment.choices}


def _notes(heads: Dict[ChannelName, InstructionUnion]) -> Set[Tuple[str, int]]:
    """The notes the heads sound, by kind of channel, the pulses one kind."""
    notes: Set[Tuple[str, int]] = set()
    for channel_name, instruction in heads.items():
        match instruction:
            case TonalInstruction(on=True):
                kind = "triangle" if channel_name == ChannelName.TRIANGLE else "pulse"
                notes.add((kind, instruction.pitch))

    return notes


@pytest.fixture(name="chord", scope="module")
def chord_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, CHORD)


class TestTheJointAssignment(BaseTestSuite):
    def test_a_chord_s_notes_head_the_columns_on_their_own_kinds_of_channel(
        self,
        chord: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher
        )

        heads = _heads(assigner.assign({0: chord}))

        assert _notes(heads) == {("pulse", 64), ("pulse", 67), ("triangle", 48)}

    def test_every_channel_held_offers_its_silence_within_the_width_the_decoder_reads(
        self,
        chord: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher
        )

        assignment = assigner.assign({0: chord})

        assert {choice.channel_name for choice in assignment.choices} == set(EVERY_CHANNEL)
        for choice in assignment.choices:
            assert len(choice.column) <= LATTICE_WIDTH
            assert any(not candidate.instruction.on for candidate in choice.column)

    def test_a_silent_frame_rests_every_channel(
        self,
        config: Config,
        extractor: FeatureExtractor,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher
        )

        assignment = assigner.assign({0: rendered_fragment(config, extractor, {})})

        assert assignment.choices == ()
        assert [rest.channel_name for rest in assignment.rests] == EVERY_CHANNEL

    def test_a_stem_counted_to_one_channel_holds_one_and_rests_the_rest(
        self,
        chord: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            _one_stem([ChannelName.PULSE1, ChannelName.PULSE2], channel_cap=1), all_channels, joint_matcher
        )

        assignment = assigner.assign({0: chord})

        assert len(assignment.choices) == 1
        assert len(assignment.rests) == 1

    def test_a_held_chord_keeps_each_pulse_note_on_its_channel(
        self,
        chord: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher
        )

        first = _pulse_pitches(_heads(assigner.assign({0: chord})))
        second = _pulse_pitches(_heads(assigner.assign({0: chord})))

        assert first == second

    def test_stems_sharing_a_channel_are_refused(
        self,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        shared = StemsConfig(
            entries=[
                StemEntry(id=0, settings=StemSettings(channels=[ChannelName.PULSE1], bends=[], channel_cap=1)),
                StemEntry(id=1, settings=StemSettings(channels=[ChannelName.PULSE1], bends=[], channel_cap=1)),
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1]], mode=HierarchyMode.ROUND_ROBIN),
        )

        with pytest.raises(ValueError, match="one stem"):
            _assigner(shared, all_channels, joint_matcher)


def _played(pool: StemPool, combination: PooledCombination) -> Dict[ChannelName, InstructionUnion]:
    return {name: candidate.instruction for name, candidate in zip(pool.channel_names, combination.candidates)}


def _pooled(pool: StemPool) -> List[Dict[ChannelName, InstructionUnion]]:
    return [_played(pool, combination) for combination in pool.combinations]


def _swapped(played: Dict[ChannelName, InstructionUnion]) -> Dict[ChannelName, InstructionUnion]:
    return {
        **played,
        ChannelName.PULSE1: played[ChannelName.PULSE2],
        ChannelName.PULSE2: played[ChannelName.PULSE1],
    }


@pytest.fixture(name="every_channel_assigner")
def every_channel_assigner_fixture(
    all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> JointAssigner:
    return _assigner(StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher)


class TestTheJointPools(BaseTestSuite):
    def test_a_sounding_frame_pools_the_choice_first(
        self, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        assignment = every_channel_assigner.assign({0: chord})

        (pool,) = assignment.pools
        assert _played(pool, pool.combinations[0]) == _heads(assignment)

    def test_every_channel_of_a_combination_carries_the_combination_s_cost(
        self, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        (pool,) = every_channel_assigner.assign({0: chord}).pools

        for combination in pool.combinations:
            assert {candidate.cost for candidate in combination.candidates} == {combination.cost}

    def test_every_combination_stands_in_both_orders_of_the_pulses(
        self, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        (pool,) = every_channel_assigner.assign({0: chord}).pools
        pooled = _pooled(pool)

        for played in pooled:
            assert _swapped(played) in pooled

    def test_the_choice_is_pooled_with_every_set_of_its_sounding_channels_silenced(
        self, chord: Fragment, every_channel_assigner: JointAssigner, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        assignment = every_channel_assigner.assign({0: chord})
        (pool,) = assignment.pools
        heads = _heads(assignment)
        sounding = [channel_name for channel_name, instruction in heads.items() if instruction.on]
        pooled = _pooled(pool)

        for count in range(1, len(sounding) + 1):
            for silenced in itertools.combinations(sounding, count):
                quiet = {name: all_channels[name].get_instruction_type().null_instruction() for name in silenced}
                assert {**heads, **quiet} in pooled

    def test_the_choice_is_pooled_with_each_channel_moved_to_every_alternative_of_its_column(
        self, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        """A path may take every move a decoder of one channel at a time could."""
        assignment = every_channel_assigner.assign({0: chord})
        (pool,) = assignment.pools
        heads = _heads(assignment)
        pooled = _pooled(pool)

        for choice in assignment.choices:
            for candidate in choice.column:
                assert {**heads, choice.channel_name: candidate.instruction} in pooled

    def test_the_previous_frame_s_choice_is_pooled(
        self, config: Config, extractor: FeatureExtractor, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        before = _heads(every_channel_assigner.assign({0: chord}))

        (pool,) = every_channel_assigner.assign({0: rendered_fragment(config, extractor, NEXT_CHORD)}).pools

        assert before in _pooled(pool)

    def test_a_silent_frame_pools_every_channel_resting(
        self, config: Config, extractor: FeatureExtractor, every_channel_assigner: JointAssigner
    ) -> None:
        (pool,) = every_channel_assigner.assign({0: rendered_fragment(config, extractor, {})}).pools

        (resting,) = pool.combinations
        assert resting.cost == RESTING_FRAME_COST
        assert not any(candidate.instruction.on for candidate in resting.candidates)

    def test_a_stem_counted_to_one_channel_pools_combinations_sounding_one(
        self, chord: Fragment, all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
    ) -> None:
        assigner = _assigner(
            _one_stem([ChannelName.PULSE1, ChannelName.PULSE2], channel_cap=1), all_channels, joint_matcher
        )

        (pool,) = assigner.assign({0: chord}).pools

        assert all(
            sum(candidate.instruction.on for candidate in combination.candidates) <= 1
            for combination in pool.combinations
        )


def _pulse_pitches(heads: Dict[ChannelName, InstructionUnion]) -> Tuple[Optional[int], Optional[int]]:
    def pitch(channel_name: ChannelName) -> Optional[int]:
        match heads.get(channel_name):
            case PulseInstruction(on=True) as instruction:
                return instruction.pitch
            case _:
                return None

    return pitch(ChannelName.PULSE1), pitch(ChannelName.PULSE2)


SEQUENCE_FRAMES: Final[int] = 12
BASS_FRAMES: Final[int] = 6
SILENT_BASS: Final[TriangleInstruction] = TriangleInstruction.null_instruction()
JUMP: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=12, duty_cycle=2)
NO_INERTIA: Final[float] = 0.0
STRONG_INERTIA: Final[float] = 100.0


def _kept(
    config: Config, lines: Mapping[ChannelName, ChannelLine], frame: int, inertia: float
) -> Dict[ChannelName, ChannelContinuity]:
    weights = TransitionWeights.of(config)
    return {channel_name: ChannelContinuity.of(line, frame, weights, inertia) for channel_name, line in lines.items()}


class TestAssigningBesideTheNeighbors(BaseTestSuite):
    """A frame assigned again among the notes its neighbors play reads only its own notes in its window."""

    @pytest.fixture(name="staccato")
    def staccato_fixture(self) -> Dict[ChannelName, List[InstructionUnion]]:
        """A bass stopping halfway under a lead held throughout."""
        lead: List[InstructionUnion] = [LEAD for _ in range(SEQUENCE_FRAMES)]
        bass: List[InstructionUnion] = [
            BASS if frame < BASS_FRAMES else SILENT_BASS for frame in range(SEQUENCE_FRAMES)
        ]
        return {ChannelName.PULSE1: lead, ChannelName.TRIANGLE: bass}

    def _beside(
        self,
        config: Config,
        window: Window,
        extractor: FeatureExtractor,
        assigner: JointAssigner,
        lines: Mapping[ChannelName, Sequence[InstructionUnion]],
        frame: int,
        *,
        played: Optional[Mapping[ChannelName, Sequence[InstructionUnion]]] = None,
        inertia: float = NO_INERTIA,
    ) -> StemFrameAssignment:
        """Assigns ``frame`` of ``played`` (``lines`` where unnamed) among neighbors decoded to play ``lines``."""
        fragments = extractor.extract(played_lines(config, lines if played is None else played, SEQUENCE_FRAMES))
        bins = len(fragments[frame].feature.values)
        profiles = frame_profiles(config, window, bins)
        silence = Contribution.silence(bins, config.library.frame_length)
        decoded = assigner.lines(decoded_lines(lines, assigner.channels, silence, SEQUENCE_FRAMES))
        heard = {channel_name: surroundings(line, frame, profiles) for channel_name, line in decoded.items()}
        return assigner.assign_beside({0: fragments[frame]}, heard, _kept(config, decoded, frame, inertia))

    def test_the_frame_after_a_bass_stops_hears_the_bass_s_tail_as_its_neighbors(
        self,
        config: Config,
        window: Window,
        extractor: FeatureExtractor,
        every_channel_assigner: JointAssigner,
        staccato: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        assignment = self._beside(config, window, extractor, every_channel_assigner, staccato, BASS_FRAMES)

        assert _notes(_heads(assignment)) == {("pulse", LEAD.pitch)}

    def test_a_frame_inside_a_held_chord_keeps_the_chord(
        self,
        config: Config,
        window: Window,
        extractor: FeatureExtractor,
        every_channel_assigner: JointAssigner,
    ) -> None:
        held = {channel_name: [instruction] * SEQUENCE_FRAMES for channel_name, instruction in CHORD.items()}

        assignment = self._beside(config, window, extractor, every_channel_assigner, held, SEQUENCE_FRAMES // 2)

        assert _notes(_heads(assignment)) == _notes(dict(CHORD))

    def test_settling_a_frame_hands_the_frames_after_it_the_frame_s_choice(
        self,
        config: Config,
        window: Window,
        extractor: FeatureExtractor,
        every_channel_assigner: JointAssigner,
        staccato: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        fragments = extractor.extract(played_lines(config, staccato, SEQUENCE_FRAMES))
        silence = Contribution.silence(len(fragments[0].feature.values), config.library.frame_length)
        silent_lead = {**staccato, ChannelName.PULSE1: [PulseInstruction.null_instruction()] * SEQUENCE_FRAMES}
        lines = every_channel_assigner.lines(
            decoded_lines(silent_lead, every_channel_assigner.channels, silence, SEQUENCE_FRAMES)
        )
        frame = BASS_FRAMES
        profiles = frame_profiles(config, window, len(fragments[frame].feature.values))
        heard = {channel_name: surroundings(line, frame, profiles) for channel_name, line in lines.items()}

        assignment = every_channel_assigner.assign_beside(
            {0: fragments[frame]}, heard, _kept(config, lines, frame, NO_INERTIA)
        )
        every_channel_assigner.settle(lines, frame, assignment)

        lead = TonalSurroundings.around(lines[ChannelName.PULSE1], frame + 1, profiles)
        assert lead.before.key == (LEAD.pitch, LEAD.duty_cycle)

    @pytest.fixture(name="jump")
    def jump_fixture(self) -> Dict[ChannelName, List[InstructionUnion]]:
        """A lead held throughout but for one frame a minor third above it."""
        middle = SEQUENCE_FRAMES // 2
        return {ChannelName.PULSE1: [JUMP if frame == middle else LEAD for frame in range(SEQUENCE_FRAMES)]}

    def test_a_frame_free_of_its_neighbors_follows_a_one_frame_jump(
        self,
        config: Config,
        window: Window,
        extractor: FeatureExtractor,
        every_channel_assigner: JointAssigner,
        jump: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        held = {ChannelName.PULSE1: [LEAD] * SEQUENCE_FRAMES}

        assignment = self._beside(
            config, window, extractor, every_channel_assigner, held, SEQUENCE_FRAMES // 2, played=jump
        )

        assert _notes(_heads(assignment)) == {("pulse", JUMP.pitch)}

    def test_a_strong_inertia_holds_a_one_frame_jump_to_the_line_beside_it(
        self,
        config: Config,
        window: Window,
        extractor: FeatureExtractor,
        every_channel_assigner: JointAssigner,
        jump: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        held = {ChannelName.PULSE1: [LEAD] * SEQUENCE_FRAMES}

        assignment = self._beside(
            config,
            window,
            extractor,
            every_channel_assigner,
            held,
            SEQUENCE_FRAMES // 2,
            played=jump,
            inertia=STRONG_INERTIA,
        )

        assert _notes(_heads(assignment)) == {("pulse", LEAD.pitch)}


class TestTheStemsMemory(BaseTestSuite):
    """The assigner keeps each stem's previous choice for the pulses' handover and the pool, cleared by a rest."""

    def test_a_frame_the_stem_leaves_silent_clears_its_previous_choice(
        self, config: Config, extractor: FeatureExtractor, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        before = _heads(every_channel_assigner.assign({0: chord}))
        every_channel_assigner.assign({0: rendered_fragment(config, extractor, {})})

        (pool,) = every_channel_assigner.assign({0: rendered_fragment(config, extractor, NEXT_CHORD)}).pools

        assert before not in _pooled(pool)

    def test_a_note_a_pulse_holds_stays_on_its_pulse_when_another_note_joins(
        self, config: Config, extractor: FeatureExtractor, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        alone = _heads(
            every_channel_assigner.assign({0: rendered_fragment(config, extractor, {ChannelName.PULSE1: HARMONY})})
        )

        joined = _heads(every_channel_assigner.assign({0: chord}))

        assert _pulse_pitches(alone) == (HARMONY.pitch, None)
        assert _pulse_pitches(joined) == (HARMONY.pitch, LEAD.pitch)


PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
LOW: Final[PulseInstruction] = PulseInstruction(on=True, pitch=60, volume=12, duty_cycle=2)
SILENT_PULSE: Final[PulseInstruction] = PulseInstruction.null_instruction()


class TestPulseHandover(BaseTestSuite):
    """The pulses go to the channels that move each least from the note it played the frame before."""

    @pytest.fixture(name="handover")
    def handover_fixture(
        self, all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
    ) -> PulseHandover:
        layout = separate_layouts(StemsConfig.single_entry(StemSettings.covering(PULSES)), all_channels)[0]
        return PulseHandover(
            layout=layout, catalog=KindCatalog.build(joint_matcher.candidate_provider, all_channels[ChannelName.PULSE1])
        )

    @staticmethod
    def _rows(handover: PulseHandover, first: PulseInstruction, second: PulseInstruction) -> Rows:
        return handover.catalog.rows_by_instruction[first], handover.catalog.rows_by_instruction[second]

    @staticmethod
    def _winner(handover: PulseHandover, first: PulseInstruction, second: PulseInstruction) -> ScoredCombination:
        silence = Contribution.silence(1, 1)
        contributions = tuple(None if not instruction.on else replace(silence) for instruction in (first, second))
        return ScoredCombination(
            rows=TestPulseHandover._rows(handover, first, second), cost=0.0, contributions=contributions, charge=0.0
        )

    def test_with_no_frame_before_a_lone_note_goes_to_the_first_pulse_with_what_it_adds(
        self, handover: PulseHandover
    ) -> None:
        winner = self._winner(handover, SILENT_PULSE, LEAD)

        handed = handover.ordered(winner, None)

        assert handed.rows == self._rows(handover, LEAD, SILENT_PULSE)
        assert handed.contributions[0] is winner.contributions[1]
        assert handed.contributions[1] is None

    def test_a_note_a_pulse_held_stays_on_it_when_another_joins(self, handover: PulseHandover) -> None:
        handed = handover.ordered(self._winner(handover, LEAD, HARMONY), self._rows(handover, HARMONY, SILENT_PULSE))

        assert handed.rows == self._rows(handover, HARMONY, LEAD)

    def test_a_note_moves_to_the_pulse_that_sounded_before_rather_than_start_on_a_silent_one(
        self, handover: PulseHandover
    ) -> None:
        handed = handover.ordered(self._winner(handover, SILENT_PULSE, LEAD), self._rows(handover, LOW, SILENT_PULSE))

        assert handed.rows == self._rows(handover, LEAD, SILENT_PULSE)

    def test_of_orders_moving_alike_the_winner_s_own_stands(self, handover: PulseHandover) -> None:
        winner = self._winner(handover, HARMONY, LEAD)

        assert handover.ordered(winner, None).rows == winner.rows

    def test_a_pulse_moves_by_its_semitones_and_starting_or_stopping_moves_the_unvoiced_distance(self) -> None:
        assert PulseHandover.moved((LEAD.pitch, None), (LOW.pitch, HARMONY.pitch)) == pytest.approx(
            LEAD.pitch - LOW.pitch + UNVOICED_DISTANCE
        )
        assert PulseHandover.moved((None, None), (None, None)) == 0.0
        assert PulseHandover.moved((None, LEAD.pitch), None) == 1.0


LOUDER_DRIVE: Final[float] = 2.0


class TestTheLines(BaseTestSuite):
    """A line holds each decoded frame as the analysis hears it: the row's power at the channel's drive."""

    @pytest.fixture(name="driven_assigner")
    def driven_assigner_fixture(
        self, all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
    ) -> JointAssigner:
        settings = StemSettings.covering(EVERY_CHANNEL).with_drive(ChannelName.PULSE1, LOUDER_DRIVE)
        return _assigner(StemsConfig.single_entry(settings), all_channels, joint_matcher)

    def test_a_decoded_frame_reads_at_its_row_s_power_over_the_drive_squared(
        self, config: Config, driven_assigner: JointAssigner
    ) -> None:
        catalog = driven_assigner.catalogs[GeneratorClassName.PULSE_GENERATOR]
        silence = Contribution.silence(catalog.powers.shape[1], config.library.frame_length)
        played = {ChannelName.PULSE1: [LEAD, HARMONY], ChannelName.PULSE2: [HARMONY, LEAD]}

        lines = driven_assigner.lines(
            decoded_lines(played, driven_assigner.channels, silence, len(played[ChannelName.PULSE1]))
        )

        lead, harmony = catalog.rows_by_instruction[LEAD], catalog.rows_by_instruction[HARMONY]
        assert np.array_equal(lines[ChannelName.PULSE1].powers, catalog.powers[[lead, harmony]] / LOUDER_DRIVE**2)
        assert np.array_equal(lines[ChannelName.PULSE2].powers, catalog.powers[[harmony, lead]])
        assert lines[ChannelName.PULSE1].keys == [catalog.key(lead), catalog.key(harmony)]
        assert lines[ChannelName.PULSE1].instructions == [LEAD, HARMONY]
        assert lines[ChannelName.PULSE1].coherent and not lines[ChannelName.NOISE].coherent

    def test_settling_a_frame_the_stem_leaves_silent_reads_every_channel_as_its_silence_at_its_drive(
        self, config: Config, extractor: FeatureExtractor, chord: Fragment, driven_assigner: JointAssigner
    ) -> None:
        catalog = driven_assigner.catalogs[GeneratorClassName.PULSE_GENERATOR]
        silence = Contribution.silence(catalog.powers.shape[1], config.library.frame_length)
        played = {ChannelName.PULSE1: [HARMONY], ChannelName.PULSE2: [HARMONY]}
        lines = driven_assigner.lines(decoded_lines(played, driven_assigner.channels, silence, 1))
        assignment = driven_assigner.assign({0: rendered_fragment(config, extractor, {})})

        driven_assigner.settle(lines, 0, assignment)

        assert lines[ChannelName.PULSE1].instructions == [PulseInstruction.null_instruction()]
        assert lines[ChannelName.PULSE1].keys == [None]
        assert np.array_equal(lines[ChannelName.PULSE1].powers[0], catalog.powers[catalog.silence] / LOUDER_DRIVE**2)
