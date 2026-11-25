from typing import Any, Dict, Final, FrozenSet, List, Mapping

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions.reconstructor.candidates import CandidateProvider
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint import proposals
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import (
    NOISE_MODES,
    KindCatalog,
    alike_timbres,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.fit import FitTarget, fitted_levels
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.hearing import SequenceHearing
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import Slot, StemLayout
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.proposals import (
    DOUBLED_NOTES,
    FREE_FIT_START,
    FREE_FIT_UPDATES,
    PROPOSED_NOTES,
    NoteDictionary,
    NoteStrengths,
    proposed_rows,
)
from sampletones_core.reconstructions.reconstructor.window.surroundings import HeldNote, TonalSurroundings
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.array import to_numpy
from tests.suite.base import BaseTestSuite

from ..conftest import (
    JOINT_DUTY_CYCLES,
    JOINT_NOISE_PERIODS,
    JOINT_PULSE_PITCHES,
    JOINT_SIGNAL_LENGTH,
    JOINT_TRIANGLE_PITCHES,
    rendered_fragment,
)
from .conftest import heard_alone, library_matcher

PULSE: Final[GeneratorClassName] = GeneratorClassName.PULSE_GENERATOR
TRIANGLE: Final[GeneratorClassName] = GeneratorClassName.TRIANGLE_GENERATOR
NOISE: Final[GeneratorClassName] = GeneratorClassName.NOISE_GENERATOR
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: LEAD,
    ChannelName.PULSE2: HARMONY,
    ChannelName.TRIANGLE: BASS,
}
LOUDER_DRIVE: Final[float] = 2.0
SOFTER_DRIVE: Final[float] = 0.5
CHORD_PULSES: Final[int] = 2
ALIKE_LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=1)
ALIKE_VOLUMES: Final[FrozenSet[int]] = frozenset({8, 12})
HALF: Final[float] = 0.5
VOLUME_STEP_OF_THE_LEAD: Final[FrozenSet[int]] = frozenset({11, LEAD.volume})


def _layout(drives: Mapping[ChannelName, float], kinds: Mapping[ChannelName, GeneratorClassName]) -> StemLayout:
    slots = tuple(Slot(channel_name=name, kind=kinds[name], drive=drive) for name, drive in drives.items())
    return StemLayout(stem_id=0, slots=slots, cap=len(slots))


KINDS: Final[Dict[ChannelName, GeneratorClassName]] = {
    ChannelName.PULSE1: PULSE,
    ChannelName.PULSE2: PULSE,
    ChannelName.TRIANGLE: TRIANGLE,
    ChannelName.NOISE: NOISE,
}


@pytest.fixture(name="catalogs", scope="module")
def catalogs_fixture(
    joint_matcher: FrameMatcher, all_channels: Dict[ChannelName, GeneratorUnion]
) -> Dict[GeneratorClassName, KindCatalog]:
    provider = joint_matcher.candidate_provider
    return {
        KINDS[name]: KindCatalog.build(provider, all_channels[name])
        for name in (ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE)
    }


@pytest.fixture(name="every_channel", scope="module")
def every_channel_fixture() -> StemLayout:
    return _layout({name: UNIT_DRIVE for name in KINDS}, KINDS)


@pytest.fixture(name="one_pulse", scope="module")
def one_pulse_fixture() -> StemLayout:
    return _layout({ChannelName.PULSE1: UNIT_DRIVE}, KINDS)


@pytest.fixture(name="every_pulse", scope="module")
def every_pulse_fixture() -> StemLayout:
    return _layout({ChannelName.PULSE1: UNIT_DRIVE, ChannelName.PULSE2: UNIT_DRIVE}, KINDS)


@pytest.fixture(name="lead", scope="module")
def lead_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, {ChannelName.PULSE1: LEAD})


@pytest.fixture(name="driven_apart", scope="module")
def driven_apart_fixture() -> StemLayout:
    return _layout(
        {ChannelName.PULSE1: LOUDER_DRIVE, ChannelName.PULSE2: SOFTER_DRIVE, ChannelName.TRIANGLE: UNIT_DRIVE}, KINDS
    )


@pytest.fixture(name="alike_matcher", scope="module")
def alike_matcher_fixture(config: Config, window: Window, extractor: FeatureExtractor) -> FrameMatcher:
    """The matcher of a library of one pulse note in the two duty cycles sharing a spectrum."""
    channels = get_generators_by_channels(config, [ChannelName.PULSE1, ChannelName.PULSE2])
    generator = channels[ChannelName.PULSE1]
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for instruction in generator.get_possible_instructions():
        alike = (
            isinstance(instruction, PulseInstruction)
            and instruction.pitch == ALIKE_LEAD.pitch
            and instruction.volume in ALIKE_VOLUMES
            and instruction.duty_cycle in alike_timbres(ALIKE_LEAD.duty_cycle)
        )
        if not instruction.on or alike:
            data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    return ReconstructorWorker(
        config=config,
        window=window,
        channels=channels,
        library_data=InstructionLibraryData.create(config, data),
        signal_length=JOINT_SIGNAL_LENGTH,
    ).matcher


@pytest.fixture(name="mute_matcher", scope="module")
def mute_matcher_fixture(config: Config) -> FrameMatcher:
    """The matcher of a library holding the pulse's silence alone."""
    return library_matcher(config, ChannelName.PULSE1, [PulseInstruction.null_instruction()])


@pytest.fixture(name="mute_catalogs", scope="module")
def mute_catalogs_fixture(
    mute_matcher: FrameMatcher, all_channels: Dict[ChannelName, GeneratorUnion]
) -> Dict[GeneratorClassName, KindCatalog]:
    """A pulse catalog sounding no note: its silent row alone."""
    return {PULSE: KindCatalog.build(mute_matcher.candidate_provider, all_channels[ChannelName.PULSE1])}


@pytest.fixture(name="chord", scope="module")
def chord_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, CHORD)


def _proposed(
    fragment: Fragment,
    layout: StemLayout,
    catalogs: Dict[GeneratorClassName, KindCatalog],
    matcher: FrameMatcher,
) -> Dict[GeneratorClassName, List[int]]:
    hearing = heard_alone(layout, catalogs, matcher.candidate_provider, len(fragment.feature.values))
    return proposed_rows(
        fragment,
        FitTarget.of(fragment, matcher.scorer.criterion),
        layout,
        NoteDictionary.of(layout, catalogs).heard(hearing),
        catalogs,
        matcher,
        hearing,
    )


def _bins(catalogs: Mapping[GeneratorClassName, KindCatalog]) -> int:
    """How many bins the library's rows, and so every frame, hold."""
    return int(next(iter(catalogs.values())).powers.shape[1])


def _features(provider: CandidateProvider, powers: np.ndarray) -> np.ndarray:
    return np.asarray(to_numpy(provider.features_of(powers)), dtype=np.float64)


def _first_rows(catalog: KindCatalog, rows: List[int]) -> Dict[int, int]:
    """Each note ``rows`` sound with the first of its rows, in the order the notes first appear."""
    first: Dict[int, int] = {}
    for row in rows:
        first.setdefault(int(catalog.notes[row]), row)

    return first


def _first_notes(catalog: KindCatalog, rows: List[int]) -> List[int]:
    """The notes ``rows`` sound, each once, in the order they first appear."""
    return list(_first_rows(catalog, rows))


class TestTheNoteDictionary(BaseTestSuite):
    """One atom per note and timbre: the note's unit row, heard on its channel as the frame hears it.

    A level of one sounds the unit row on the atom's channel at the channel's drive, and the cap and
    the power move with the atom, so the most a note sounds is what every channel of its kind plays.
    """

    def test_an_atom_stands_for_each_note_in_each_timbre_kind_by_kind_in_name_order(
        self, every_channel: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        dictionary = NoteDictionary.of(every_channel, catalogs)

        expected = [
            *((NOISE, NOISE_MODES * period) for period in sorted(JOINT_NOISE_PERIODS)),
            *((PULSE, pitch) for pitch in sorted(JOINT_PULSE_PITCHES) for _ in JOINT_DUTY_CYCLES),
            *((TRIANGLE, pitch) for pitch in sorted(JOINT_TRIANGLE_PITCHES)),
        ]
        assert list(zip(dictionary.kinds, dictionary.notes.tolist())) == expected

    def test_an_atom_heard_alone_is_its_note_s_loudest_row_at_its_channel_s_drive_its_power_that_row_s_whole(
        self, driven_apart: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        """A frame heard alone hears every pulse on the first pulse, which the stem drives harder."""
        provider = joint_matcher.candidate_provider
        hearing = heard_alone(driven_apart, catalogs, provider, _bins(catalogs))
        atoms = NoteDictionary.of(driven_apart, catalogs).heard(hearing)
        pulses = catalogs[PULSE]
        first = atoms.kinds.index(PULSE)

        for offset, duty_cycle in enumerate(sorted(JOINT_DUTY_CYCLES)):
            loudest = pulses.powers[pulses.loudest(min(JOINT_PULSE_PITCHES), duty_cycle)]
            assert atoms.features[first + offset] == pytest.approx(_features(provider, loudest / LOUDER_DRIVE**2))
            assert atoms.powers[first + offset] == pytest.approx(loudest.sum() / LOUDER_DRIVE**2)

    def test_an_atom_reaches_every_channel_of_its_kind_playing_it_at_full_volume_at_its_drive(
        self, driven_apart: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        """At its cap an atom sounds its note at full volume on every channel of its kind, each at its own drive."""
        hearing = heard_alone(driven_apart, catalogs, joint_matcher.candidate_provider, _bins(catalogs))
        dictionary = NoteDictionary.of(driven_apart, catalogs)
        atoms = dictionary.heard(hearing)

        for atom, (kind, row) in enumerate(zip(dictionary.kinds, dictionary.rows)):
            catalog = catalogs[kind]
            unit = catalog.unit_of(int(row))
            shares = sum(1.0 / slot.drive**2 for slot in driven_apart.of_kind(kind))
            at_full_volume = unit.full_level * catalog.powers[unit.row].sum() * shares
            assert atoms.caps[atom] * atoms.powers[atom] == pytest.approx(at_full_volume)

    def test_a_cap_at_drive_two_reaches_the_loudest_row_at_that_drive(
        self, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        """The atom on a pulse driven at two sounds a quarter of its row's power, and its cap reaches that quarter.

        A cap left at what a channel at unit drive reaches would count the drive twice.
        """
        provider = joint_matcher.candidate_provider
        driven = _layout({ChannelName.PULSE1: LOUDER_DRIVE}, KINDS)
        dictionary = NoteDictionary.of(driven, catalogs)
        atoms = dictionary.heard(heard_alone(driven, catalogs, provider, _bins(catalogs)))
        pulses = catalogs[PULSE]

        for atom, row in enumerate(dictionary.rows):
            loudest = pulses.powers[pulses.loudest(int(pulses.notes[row]), int(pulses.timbres[row]))]
            assert atoms.caps[atom] * atoms.powers[atom] == pytest.approx(loudest.sum() / LOUDER_DRIVE**2)
            assert atoms.caps[atom] * atoms.features[atom] == pytest.approx(
                _features(provider, loudest / LOUDER_DRIVE**2)
            )

    def test_a_note_s_strength_is_its_atoms_fitted_power_over_every_timbre(
        self, every_channel: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        hearing = heard_alone(every_channel, catalogs, joint_matcher.candidate_provider, _bins(catalogs))
        atoms = NoteDictionary.of(every_channel, catalogs).heard(hearing)
        levels = np.linspace(0.1, 1.0, len(atoms.kinds))

        strengths = atoms.strengths(levels).strengths

        note = int(LEAD.pitch)
        chosen = [atom for atom, kind in enumerate(atoms.kinds) if kind == PULSE and atoms.notes[atom] == note]
        assert len(chosen) == len(JOINT_DUTY_CYCLES)
        assert strengths[(PULSE, note)] == pytest.approx(sum(levels[atom] * atoms.powers[atom] for atom in chosen))

    def test_a_stem_whose_kinds_sound_no_note_has_no_atom_over_the_bins(
        self,
        one_pulse: StemLayout,
        mute_catalogs: Dict[GeneratorClassName, KindCatalog],
        mute_matcher: FrameMatcher,
    ) -> None:
        bins = _bins(mute_catalogs)
        dictionary = NoteDictionary.of(one_pulse, mute_catalogs)

        atoms = dictionary.heard(heard_alone(one_pulse, mute_catalogs, mute_matcher.candidate_provider, bins))

        assert atoms.features.shape == (0, bins)
        assert not atoms.kinds
        assert not atoms.caps.size
        assert not atoms.powers.size

    def test_the_fit_of_no_atom_gives_no_levels(
        self,
        lead: Fragment,
        one_pulse: StemLayout,
        mute_catalogs: Dict[GeneratorClassName, KindCatalog],
        mute_matcher: FrameMatcher,
    ) -> None:
        hearing = heard_alone(one_pulse, mute_catalogs, mute_matcher.candidate_provider, _bins(mute_catalogs))
        atoms = NoteDictionary.of(one_pulse, mute_catalogs).heard(hearing)
        target = FitTarget.of(lead, mute_matcher.scorer.criterion)

        levels = fitted_levels(
            target,
            atoms.features,
            atoms.caps,
            base=np.zeros_like(target.reference),
            start=FREE_FIT_START,
            updates=FREE_FIT_UPDATES,
        )

        assert levels.shape == (0,)
        assert not atoms.strengths(levels).strengths


class TestNoteStrengths(BaseTestSuite):
    """A kind's notes ranked by strength, the lower of equally strong notes first, notes of no strength left out."""

    @pytest.fixture(name="strengths")
    def strengths_fixture(self) -> NoteStrengths:
        return NoteStrengths(
            strengths={
                (PULSE, 48): 1.0,
                (PULSE, 57): 3.0,
                (PULSE, 60): 3.0,
                (PULSE, 64): 0.0,
                (TRIANGLE, 45): 5.0,
            }
        )

    def test_a_kind_s_notes_come_strongest_first_and_equal_ones_lower_first(self, strengths: NoteStrengths) -> None:
        assert strengths.strongest(PULSE, len(JOINT_PULSE_PITCHES)) == [57, 60, 48]

    def test_a_kind_proposes_at_most_its_count(self, strengths: NoteStrengths) -> None:
        assert strengths.strongest(PULSE, 2) == [57, 60]

    def test_a_note_of_no_strength_is_left_out_within_the_count(self, strengths: NoteStrengths) -> None:
        assert strengths.strongest(PULSE, 4) == [57, 60, 48]

    def test_a_kind_without_notes_proposes_none(self, strengths: NoteStrengths) -> None:
        assert not strengths.strongest(NOISE, PROPOSED_NOTES[NOISE])


class TestProposedRows(BaseTestSuite):
    """A frame's strongest notes of each kind, each on its best row alone."""

    def test_a_stem_whose_kinds_sound_no_note_proposes_nothing(
        self,
        lead: Fragment,
        one_pulse: StemLayout,
        mute_catalogs: Dict[GeneratorClassName, KindCatalog],
        mute_matcher: FrameMatcher,
    ) -> None:
        assert _proposed(lead, one_pulse, mute_catalogs, mute_matcher) == {PULSE: []}

    def test_a_chord_s_notes_are_proposed_on_their_own_kinds(
        self,
        chord: Fragment,
        every_channel: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        proposed = _proposed(chord, every_channel, catalogs, joint_matcher)

        assert set(proposed) == {PULSE, TRIANGLE, NOISE}
        assert {LEAD.pitch, HARMONY.pitch} <= set(_first_notes(catalogs[PULSE], proposed[PULSE]))
        assert BASS.pitch in _first_notes(catalogs[TRIANGLE], proposed[TRIANGLE])

    def test_the_two_strongest_pulse_notes_of_a_two_pulse_chord_are_its_notes(
        self,
        chord: Fragment,
        every_channel: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(proposals, "PROPOSED_NOTES", {**PROPOSED_NOTES, PULSE: CHORD_PULSES})

        proposed = _proposed(chord, every_channel, catalogs, joint_matcher)

        assert set(_first_notes(catalogs[PULSE], proposed[PULSE])) == {LEAD.pitch, HARMONY.pitch}

    def test_a_proposed_note_sounds_on_the_row_the_frame_plays_it_on(
        self,
        chord: Fragment,
        every_channel: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        """Its shortfall counted lightly, a row alone is chosen by its own note's bins: its duty cycle and volume.

        Counted in full, the frame's other notes would ask every note for its loudest row.
        """
        pulses = catalogs[PULSE]
        proposed = _proposed(chord, every_channel, catalogs, joint_matcher)

        first_rows = _first_rows(pulses, proposed[PULSE])
        assert pulses.instructions[first_rows[LEAD.pitch]] == LEAD
        assert pulses.instructions[first_rows[HARMONY.pitch]] == HARMONY

    def test_each_kind_proposes_at_most_its_count_of_notes(
        self,
        chord: Fragment,
        every_channel: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        counts = {kind: 1 for kind in PROPOSED_NOTES}
        monkeypatch.setattr(proposals, "PROPOSED_NOTES", counts)

        proposed = _proposed(chord, every_channel, catalogs, joint_matcher)

        for kind, rows in proposed.items():
            assert len(_first_notes(catalogs[kind], rows)) == counts[kind]

    def test_with_two_pulses_the_strongest_notes_return_on_a_duty_cycle_sounding_unlike_their_first(
        self,
        chord: Fragment,
        every_channel: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        pulses = catalogs[PULSE]
        rows = _proposed(chord, every_channel, catalogs, joint_matcher)[PULSE]
        notes = _first_notes(pulses, rows)

        firsts, seconds = rows[: len(notes)], rows[len(notes) :]

        assert len(seconds) == min(DOUBLED_NOTES, len(notes))
        for first, second in zip(firsts, seconds):
            assert pulses.notes[second] == pulses.notes[first]
            assert int(pulses.timbres[second]) not in alike_timbres(int(pulses.timbres[first]))

    def test_a_note_held_only_in_duty_cycles_sounding_alike_has_no_second_duty_cycle(
        self, config: Config, extractor: FeatureExtractor, alike_matcher: FrameMatcher
    ) -> None:
        generator = get_generators_by_channels(config, [ChannelName.PULSE1])[ChannelName.PULSE1]
        catalogs = {PULSE: KindCatalog.build(alike_matcher.candidate_provider, generator)}
        layout = _layout({ChannelName.PULSE1: UNIT_DRIVE, ChannelName.PULSE2: UNIT_DRIVE}, KINDS)
        frame = rendered_fragment(config, extractor, {ChannelName.PULSE1: ALIKE_LEAD})

        (row,) = _proposed(frame, layout, catalogs, alike_matcher)[PULSE]

        assert catalogs[PULSE].notes[row] == ALIKE_LEAD.pitch

    def test_a_proposal_extending_a_note_a_pulse_holds_is_tried_joined_to_it_on_that_pulse(
        self,
        lead: Fragment,
        every_pulse: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        """The second pulse holds the lead up to the frame at half of every bin's window.

        Joined to it, the lead's own row brings the frame to the lead's whole power, so the proposal
        lands within a library step of the lead's volume, the shortfall counted lightly leaning to the
        quieter one. Heard on the first pulse, which holds nothing, every row would sound over the held
        note's leak, and a far quieter one would fit.
        """
        pulses = {PULSE: catalogs[PULSE]}
        lead_row = catalogs[PULSE].rows_by_instruction[LEAD]
        amplitude = np.sqrt(catalogs[PULSE].powers[lead_row])
        bins = amplitude.shape[0]
        held = HeldNote(
            key=catalogs[PULSE].key(lead_row), frames=range(0, 1), amplitude=HALF * amplitude, share=np.full(bins, HALF)
        )
        surroundings = [
            TonalSurroundings(
                leak=np.zeros(bins), before=HeldNote.silence(bins), after=HeldNote.silence(bins), own=np.ones(bins)
            ),
            TonalSurroundings(leak=held.power, before=held, after=HeldNote.silence(bins), own=np.full(bins, HALF)),
        ]
        hearing = SequenceHearing.of(every_pulse, pulses, surroundings, joint_matcher.candidate_provider)

        proposed = proposed_rows(
            lead,
            FitTarget.of(lead, joint_matcher.scorer.criterion),
            every_pulse,
            NoteDictionary.of(every_pulse, pulses).heard(hearing),
            pulses,
            joint_matcher,
            hearing,
        )

        row = _first_rows(catalogs[PULSE], proposed[PULSE])[LEAD.pitch]
        assert int(catalogs[PULSE].timbres[row]) == LEAD.duty_cycle
        assert int(catalogs[PULSE].volumes[row]) in VOLUME_STEP_OF_THE_LEAD

    def test_with_one_pulse_each_note_is_proposed_once(
        self,
        chord: Fragment,
        one_pulse: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        proposed = _proposed(chord, one_pulse, catalogs, joint_matcher)

        assert set(proposed) == {PULSE}
        assert len(_first_notes(catalogs[PULSE], proposed[PULSE])) == len(proposed[PULSE])
