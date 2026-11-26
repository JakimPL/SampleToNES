from dataclasses import dataclass
from typing import Dict, Final, List, Optional, Sequence

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.library import InstructionsLibraryConfig
from sampletones_core.constants.enums import ChannelName, GeneratorClassName, SpectrumMethod
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_core.reconstructions.reconstructor.candidates import CandidateProvider
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.hearing import (
    SequenceHearing,
    rows_by_place,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import Slot, StemLayout
from sampletones_core.reconstructions.reconstructor.window.profiles import FrameProfiles, frame_profiles
from sampletones_core.reconstructions.reconstructor.window.surroundings import (
    ChannelLine,
    ChannelSurroundings,
    HeldNote,
    NoiseSurroundings,
    NoteKey,
    TonalSurroundings,
    surroundings,
)
from sampletones_shared.array import to_numpy
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from ..conftest import rendered_fragment
from .conftest import heard_alone, library_matcher

PULSE: Final[GeneratorClassName] = GeneratorClassName.PULSE_GENERATOR
NOISE: Final[GeneratorClassName] = GeneratorClassName.NOISE_GENERATOR
HELD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
OTHER: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
QUIET: Final[PulseInstruction] = PulseInstruction.null_instruction()
HIT: Final[NoiseInstruction] = NoiseInstruction(on=True, period=4, volume=15, short=False)
FIRST_DRIVE: Final[float] = 2.0
SECOND_DRIVE: Final[float] = 0.5
FIRST_LEAK: Final[float] = 0.25
SECOND_LEAK: Final[float] = 0.5
HALF_SHARE: Final[float] = 0.5
FRAMES: Final[int] = 9
MIDDLE: Final[int] = 4
WINDOW_METHODS: Final[List[SpectrumMethod]] = [SpectrumMethod.CQT, SpectrumMethod.FFT]
LINEAR_GAMMA: Final[int] = 0
CURVED_GAMMA: Final[int] = 50


@pytest.fixture(name="catalogs", scope="module")
def catalogs_fixture(
    all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> Dict[GeneratorClassName, KindCatalog]:
    provider = joint_matcher.candidate_provider
    return {
        PULSE: KindCatalog.build(provider, all_channels[ChannelName.PULSE1]),
        NOISE: KindCatalog.build(provider, all_channels[ChannelName.NOISE]),
    }


@pytest.fixture(name="pulses", scope="module")
def pulses_fixture() -> StemLayout:
    """Two pulses the stem drives unlike, so a row read at the wrong channel's drive shows."""
    return StemLayout(
        stem_id=0,
        slots=(
            Slot(channel_name=ChannelName.PULSE1, kind=PULSE, drive=FIRST_DRIVE),
            Slot(channel_name=ChannelName.PULSE2, kind=PULSE, drive=SECOND_DRIVE),
        ),
        cap=2,
    )


@pytest.fixture(name="pulse_and_noise", scope="module")
def pulse_and_noise_fixture() -> StemLayout:
    return StemLayout(
        stem_id=0,
        slots=(
            Slot(channel_name=ChannelName.PULSE1, kind=PULSE, drive=FIRST_DRIVE),
            Slot(channel_name=ChannelName.NOISE, kind=NOISE, drive=SECOND_DRIVE),
        ),
        cap=2,
    )


@pytest.fixture(name="provider", scope="module")
def provider_fixture(joint_matcher: FrameMatcher) -> CandidateProvider:
    return joint_matcher.candidate_provider


@pytest.fixture(name="bins", scope="module")
def bins_fixture(catalogs: Dict[GeneratorClassName, KindCatalog]) -> int:
    return int(catalogs[PULSE].powers.shape[1])


@pytest.fixture(name="fragment", scope="module")
def fragment_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, {ChannelName.PULSE1: HELD})


def _rows(catalog: KindCatalog, instructions: Sequence[InstructionUnion]) -> List[int]:
    return [catalog.rows_by_instruction[instruction] for instruction in instructions]


def _features(provider: CandidateProvider, powers: np.ndarray) -> np.ndarray:
    return np.asarray(to_numpy(provider.features_of(powers)), dtype=np.float64)


def _tonal(bins: int, *, leak: float, own: float, held: Optional[NoteKey]) -> TonalSurroundings:
    """A tonal channel whose frame holds ``own`` of every bin's window, with ``held`` held up to it at unit amplitude."""
    before = HeldNote.silence(bins)
    if held is not None:
        before = HeldNote(key=held, frames=range(0, 1), amplitude=np.ones(bins), share=np.full(bins, 1.0 - own))

    return TonalSurroundings(
        leak=np.full(bins, leak), before=before, after=HeldNote.silence(bins), own=np.full(bins, own)
    )


def _line(
    catalog: KindCatalog, instructions: Sequence[InstructionUnion], drive: float, *, coherent: bool
) -> ChannelLine:
    """A channel's frames playing ``instructions``, read at ``drive``."""
    rows = _rows(catalog, instructions)
    return ChannelLine(
        keys=[catalog.key(row) for row in rows],
        powers=catalog.powers[rows] / drive**2,
        instructions=list(instructions),
        coherent=coherent,
    )


class TestAFrameHeardAlone(BaseTestSuite):
    """A frame heard alone hears every row as a note held through the whole window, at its channel's drive."""

    @pytest.mark.parametrize("place", [0, 1], ids=["first", "second"])
    def test_a_row_adds_its_library_power_at_its_channel_s_drive(
        self,
        place: int,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        rows = _rows(catalogs[PULSE], [HELD, OTHER])
        hearing = heard_alone(pulses, catalogs, provider, bins)

        assert np.array_equal(
            hearing.powers(place, rows), catalogs[PULSE].powers[rows] / pulses.slots[place].drive ** 2
        )

    @pytest.mark.parametrize("place", [0, 1], ids=["first", "second"])
    def test_a_fit_reads_a_row_in_the_feature_values_of_its_power(
        self,
        place: int,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        rows = _rows(catalogs[PULSE], [HELD, OTHER, QUIET])
        hearing = heard_alone(pulses, catalogs, provider, bins)

        assert np.array_equal(hearing.unit_powers(place, rows), hearing.powers(place, rows))
        assert hearing.unit_features(place, rows) == pytest.approx(_features(provider, hearing.powers(place, rows)))

    def test_the_frame_holds_nothing_before_its_rows_sound(
        self,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
        fragment: Fragment,
    ) -> None:
        hearing = heard_alone(pulses, catalogs, provider, bins)

        mix = hearing.empty_mix(fragment)

        assert not hearing.leak.any()
        assert not hearing.leak_features.any()
        assert not mix.power.any()
        assert (mix.variance, mix.sounding) == (0.0, 0)

    def test_every_proposal_is_heard_on_the_first_channel_of_its_kind(
        self,
        pulse_and_noise: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        hearing = heard_alone(pulse_and_noise, catalogs, provider, bins)

        assert hearing.place_of(PULSE, catalogs[PULSE].rows_by_instruction[HELD]) == 0
        assert hearing.place_of(NOISE, catalogs[NOISE].rows_by_instruction[HIT]) == 1


@pytest.fixture(name="curved", scope="module", params=[LINEAR_GAMMA, CURVED_GAMMA], ids=["gamma_0", "gamma_50"])
def curved_fixture(request: pytest.FixtureRequest) -> CandidateProvider:
    """The provider of a library of the cases' pulse rows, its features read at the gamma given."""
    config = Config(library=InstructionsLibraryConfig(transformation_gamma=request.param))
    return library_matcher(config, ChannelName.PULSE1, [QUIET, HELD, OTHER]).candidate_provider


class TestAFrameHeardAloneAtEveryGamma(BaseTestSuite):
    """A frame heard alone reads each row's feature values as a frame among silent neighbors reads them.

    The frame among its neighbors holds the whole of every bin's window as its own share, so it hears
    each row whole, and a row's feature values are the transform of the power it adds at its channel's
    drive. A transformation gamma of zero reads power linearly, and fifty reads it through a curve.
    """

    @pytest.mark.parametrize("place", [0, 1], ids=["first", "second"])
    def test_a_row_reads_as_the_frame_among_silent_neighbors_reads_it(
        self, place: int, pulses: StemLayout, all_channels: Dict[ChannelName, GeneratorUnion], curved: CandidateProvider
    ) -> None:
        catalogs = {PULSE: KindCatalog.build(curved, all_channels[ChannelName.PULSE1])}
        bins = int(catalogs[PULSE].powers.shape[1])
        rows = _rows(catalogs[PULSE], [HELD, OTHER, QUIET])
        silent = [_tonal(bins, leak=0.0, own=1.0, held=None), _tonal(bins, leak=0.0, own=1.0, held=None)]

        alone = heard_alone(pulses, catalogs, curved, bins)

        among = SequenceHearing.of(pulses, catalogs, silent, curved)
        assert alone.unit_features(place, rows) == pytest.approx(among.unit_features(place, rows))


class TestAFrameHeardAmongItsNeighbors(BaseTestSuite):
    """A frame among its neighbors holds their leak in every mix and hears each row through its channel's surroundings."""

    def test_the_stem_s_leak_is_its_channels_leaks_summed(
        self,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        around = [
            _tonal(bins, leak=FIRST_LEAK, own=1.0, held=None),
            _tonal(bins, leak=SECOND_LEAK, own=1.0, held=None),
        ]

        hearing = SequenceHearing.of(pulses, catalogs, around, provider)

        leak = np.full(bins, FIRST_LEAK + SECOND_LEAK)
        assert hearing.leak == pytest.approx(leak)
        assert hearing.leak_features == pytest.approx(_features(provider, leak[None, :])[0])

    def test_the_leak_sounds_in_a_mix_s_power_alone(
        self,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
        fragment: Fragment,
    ) -> None:
        """The leak is what the window reads of the other frames, and the frame's own samples sound none of it."""
        around = [
            _tonal(bins, leak=FIRST_LEAK, own=1.0, held=None),
            _tonal(bins, leak=SECOND_LEAK, own=1.0, held=None),
        ]
        hearing = SequenceHearing.of(pulses, catalogs, around, provider)

        mix = hearing.empty_mix(fragment)

        silence = FrameMix.empty(fragment)
        assert mix.power == pytest.approx(hearing.leak)
        assert np.array_equal(mix.expectation, silence.expectation)
        assert (mix.variance, mix.sounding) == (silence.variance, silence.sounding)

    @pytest.mark.parametrize("place", [0, 1], ids=["first", "second"])
    def test_a_row_is_heard_through_its_own_channel_s_surroundings_at_its_drive(
        self,
        place: int,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        catalog = catalogs[PULSE]
        rows = _rows(catalog, [HELD, OTHER, QUIET])
        keys = [catalog.key(row) for row in rows]
        held_key = catalog.key(catalog.rows_by_instruction[HELD])
        around: List[ChannelSurroundings] = [
            _tonal(bins, leak=FIRST_LEAK, own=1.0, held=None),
            _tonal(bins, leak=SECOND_LEAK, own=HALF_SHARE, held=held_key),
        ]
        hearing = SequenceHearing.of(pulses, catalogs, around, provider)
        library = catalog.powers[rows] / pulses.slots[place].drive ** 2

        assert hearing.powers(place, rows) == pytest.approx(around[place].heard(keys, library))
        assert hearing.unit_powers(place, rows) == pytest.approx(around[place].gains(keys) * library)
        assert hearing.unit_features(place, rows) == pytest.approx(
            _features(provider, hearing.unit_powers(place, rows))
        )

    def test_a_noise_row_is_heard_by_its_share_of_squared_weight(
        self,
        pulse_and_noise: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        noise = NoiseSurroundings(leak=np.zeros(bins), own=np.full(bins, HALF_SHARE))
        hearing = SequenceHearing.of(
            pulse_and_noise, catalogs, [_tonal(bins, leak=0.0, own=1.0, held=None), noise], provider
        )
        rows = _rows(catalogs[NOISE], [HIT])

        library = catalogs[NOISE].powers[rows] / SECOND_DRIVE**2
        assert hearing.powers(1, rows) == pytest.approx(HALF_SHARE * library)
        assert hearing.place_of(NOISE, rows[0]) == 1


class TestWhereAProposalIsHeard(BaseTestSuite):
    """A proposed row is heard on the channel whose held note it extends, the first of its kind otherwise."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        held_first: bool
        held_second: bool
        proposed: PulseInstruction
        expected: int

    test_cases = (
        TestCase(label="held_on_neither", held_first=False, held_second=False, proposed=HELD, expected=0),
        TestCase(label="held_on_the_second", held_first=False, held_second=True, proposed=HELD, expected=1),
        TestCase(label="held_on_the_first", held_first=True, held_second=False, proposed=HELD, expected=0),
        TestCase(label="held_on_both", held_first=True, held_second=True, proposed=HELD, expected=0),
        TestCase(label="unlike_the_held_note", held_first=False, held_second=True, proposed=OTHER, expected=0),
        TestCase(label="silent", held_first=False, held_second=True, proposed=QUIET, expected=0),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_proposal_joins_the_channel_holding_its_note(
        self,
        test_case: TestCase,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        catalog = catalogs[PULSE]
        held_key = catalog.key(catalog.rows_by_instruction[HELD])
        around = [
            _tonal(bins, leak=0.0, own=HALF_SHARE, held=held_key if test_case.held_first else None),
            _tonal(bins, leak=0.0, own=HALF_SHARE, held=held_key if test_case.held_second else None),
        ]
        hearing = SequenceHearing.of(pulses, catalogs, around, provider)

        assert hearing.place_of(PULSE, catalog.rows_by_instruction[test_case.proposed]) == test_case.expected

    def test_rows_are_read_together_on_the_channel_hearing_each(
        self,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        """The second pulse holds the note, so its rows go there and the others to the first pulse, each in order."""
        catalog = catalogs[PULSE]
        held_key = catalog.key(catalog.rows_by_instruction[HELD])
        around = [
            _tonal(bins, leak=0.0, own=HALF_SHARE, held=None),
            _tonal(bins, leak=0.0, own=HALF_SHARE, held=held_key),
        ]
        hearing = SequenceHearing.of(pulses, catalogs, around, provider)
        rows = np.array(_rows(catalog, [OTHER, HELD, QUIET, HELD]))

        grouped = rows_by_place(hearing, PULSE, rows)

        assert [(place, positions.tolist()) for place, positions in grouped] == [(0, [0, 2]), (1, [1, 3])]
        assert not rows_by_place(hearing, PULSE, rows[:0])


class TestHearingAFrameOfALine(BaseTestSuite):
    """A frame of decoded lines, heard among them as each window method reads the frames around it."""

    @staticmethod
    def _profiles(method: SpectrumMethod, bins: int) -> FrameProfiles:
        config = Config(library=InstructionsLibraryConfig(spectrum_method=method))
        return frame_profiles(config, Window.from_config(config), bins)

    @staticmethod
    def _hearing(
        layout: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        lines: List[ChannelLine],
        frame: int,
        profiles: FrameProfiles,
        provider: CandidateProvider,
    ) -> SequenceHearing:
        return SequenceHearing.of(layout, catalogs, [surroundings(line, frame, profiles) for line in lines], provider)

    @pytest.mark.parametrize("method", WINDOW_METHODS, ids=[method.value for method in WINDOW_METHODS])
    def test_a_note_held_through_the_frame_is_heard_as_the_frame_heard_alone_hears_it(
        self,
        method: SpectrumMethod,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        catalog = catalogs[PULSE]
        frames = 2 * self._profiles(method, bins).reach + 1
        lines = [
            _line(catalog, [HELD] * frames, FIRST_DRIVE, coherent=True),
            _line(catalog, [QUIET] * frames, SECOND_DRIVE, coherent=True),
        ]
        steady = heard_alone(pulses, catalogs, provider, bins)
        rows = _rows(catalog, [HELD])

        hearing = self._hearing(pulses, catalogs, lines, frames // 2, self._profiles(method, bins), provider)

        assert hearing.leak + hearing.powers(0, rows)[0] == pytest.approx(steady.powers(0, rows)[0])

    @pytest.mark.parametrize("method", WINDOW_METHODS, ids=[method.value for method in WINDOW_METHODS])
    def test_a_window_reaching_past_the_line_s_ends_reads_silence_there(
        self,
        method: SpectrumMethod,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        catalog = catalogs[PULSE]
        profiles = self._profiles(method, bins)
        lines = [
            _line(catalog, [HELD] * FRAMES, FIRST_DRIVE, coherent=True),
            _line(catalog, [QUIET] * FRAMES, SECOND_DRIVE, coherent=True),
        ]
        steady = heard_alone(pulses, catalogs, provider, bins)
        rows = _rows(catalog, [HELD])

        hearing = self._hearing(pulses, catalogs, lines, 0, profiles, provider)

        from_the_start = profiles.amplitude[profiles.reach : profiles.reach + FRAMES].sum(axis=0)
        expected = np.square(from_the_start) * steady.powers(0, rows)[0]
        assert hearing.leak + hearing.powers(0, rows)[0] == pytest.approx(expected)

    @pytest.mark.parametrize("method", WINDOW_METHODS, ids=[method.value for method in WINDOW_METHODS])
    def test_a_note_held_up_to_the_frame_leaves_its_tail_and_a_row_unlike_it_its_own_share(
        self,
        method: SpectrumMethod,
        pulses: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        catalog = catalogs[PULSE]
        profiles = self._profiles(method, bins)
        lines = [
            _line(catalog, [HELD] * MIDDLE + [QUIET] * (FRAMES - MIDDLE), FIRST_DRIVE, coherent=True),
            _line(catalog, [QUIET] * FRAMES, SECOND_DRIVE, coherent=True),
        ]
        steady = heard_alone(pulses, catalogs, provider, bins)

        hearing = self._hearing(pulses, catalogs, lines, MIDDLE, profiles, provider)

        tail = profiles.amplitude[max(0, profiles.reach - MIDDLE) : profiles.reach].sum(axis=0)
        held_power = steady.powers(0, _rows(catalog, [HELD]))[0]
        other_rows = _rows(catalog, [OTHER])
        assert hearing.leak == pytest.approx(np.square(tail) * held_power)
        assert hearing.powers(0, other_rows)[0] == pytest.approx(
            np.square(profiles.own_amplitude) * steady.powers(0, other_rows)[0]
        )

    @pytest.mark.parametrize("method", WINDOW_METHODS, ids=[method.value for method in WINDOW_METHODS])
    def test_the_frame_of_a_one_frame_line_hears_each_row_by_its_own_share_alone(
        self,
        method: SpectrumMethod,
        pulse_and_noise: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        profiles = self._profiles(method, bins)
        lines = [
            _line(catalogs[PULSE], [QUIET], FIRST_DRIVE, coherent=True),
            _line(catalogs[NOISE], [NoiseInstruction.null_instruction()], SECOND_DRIVE, coherent=False),
        ]
        steady = heard_alone(pulse_and_noise, catalogs, provider, bins)
        pulse_rows = _rows(catalogs[PULSE], [HELD])
        noise_rows = _rows(catalogs[NOISE], [HIT])

        hearing = self._hearing(pulse_and_noise, catalogs, lines, 0, profiles, provider)

        assert not hearing.leak.any()
        assert hearing.powers(0, pulse_rows)[0] == pytest.approx(
            np.square(profiles.own_amplitude) * steady.powers(0, pulse_rows)[0]
        )
        assert hearing.powers(1, noise_rows)[0] == pytest.approx(profiles.own_energy * steady.powers(1, noise_rows)[0])

    @pytest.mark.parametrize("method", WINDOW_METHODS, ids=[method.value for method in WINDOW_METHODS])
    def test_a_frame_among_silence_holds_nothing_and_a_silent_row_adds_nothing(
        self,
        method: SpectrumMethod,
        pulse_and_noise: StemLayout,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        bins: int,
        provider: CandidateProvider,
    ) -> None:
        silent_noise = NoiseInstruction.null_instruction()
        lines = [
            _line(catalogs[PULSE], [QUIET] * FRAMES, FIRST_DRIVE, coherent=True),
            _line(catalogs[NOISE], [silent_noise] * FRAMES, SECOND_DRIVE, coherent=False),
        ]

        hearing = self._hearing(pulse_and_noise, catalogs, lines, MIDDLE, self._profiles(method, bins), provider)

        assert not hearing.leak.any()
        assert not hearing.leak_features.any()
        assert not hearing.powers(0, _rows(catalogs[PULSE], [QUIET])).any()
        assert not hearing.powers(1, _rows(catalogs[NOISE], [silent_noise])).any()
