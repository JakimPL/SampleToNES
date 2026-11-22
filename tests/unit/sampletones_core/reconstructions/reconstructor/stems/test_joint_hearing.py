from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.hearing import (
    SequenceHearing,
    SteadyHearing,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout, separate_layouts
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.window.surroundings import HeldNote, TonalSurroundings

from ..conftest import rendered_fragment

PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
HELD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
OTHER: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
LEAK: Final[float] = 0.25


@pytest.fixture(name="pulse_layout", scope="module")
def pulse_layout_fixture(all_channels: Dict[ChannelName, GeneratorUnion]) -> StemLayout:
    return separate_layouts(StemsConfig.single_entry(StemSettings.covering(PULSES)), all_channels)[0]


@pytest.fixture(name="pulse_catalogs", scope="module")
def pulse_catalogs_fixture(
    all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> Dict[GeneratorClassName, KindCatalog]:
    catalog = KindCatalog.build(joint_matcher.candidate_provider, all_channels[ChannelName.PULSE1])
    return {GeneratorClassName.PULSE_GENERATOR: catalog}


def _alone(bins: int, *, leak: float = 0.0, held: bool = False) -> TonalSurroundings:
    """A channel whose frame reads its own frame alone, ``leak`` in every bin, a held note before it when asked."""
    held_note = HeldNote(
        key=(HELD.pitch, HELD.duty_cycle), frames=range(0, 1), amplitude=np.ones(bins), share=np.zeros(bins)
    )
    return TonalSurroundings(
        leak=np.full(bins, leak),
        before=held_note if held else HeldNote.silence(bins),
        after=HeldNote.silence(bins),
        own=np.ones(bins),
    )


class TestHowAFrameHearsItsRows:
    def test_a_frame_heard_alone_adds_each_row_s_library_power(
        self, pulse_layout: StemLayout, pulse_catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        catalog = pulse_catalogs[GeneratorClassName.PULSE_GENERATOR]
        rows = [catalog.rows_by_instruction[HELD], catalog.rows_by_instruction[OTHER]]
        hearing = SteadyHearing(layout=pulse_layout, catalogs=pulse_catalogs, bins=catalog.powers.shape[1])

        expected = catalog.powers[rows] / pulse_layout.slots[0].drive ** 2
        assert np.array_equal(hearing.powers(0, rows), expected)
        assert not hearing.leak.any()

    def test_a_frame_whose_window_reads_it_alone_hears_its_rows_as_a_frame_heard_alone(
        self,
        pulse_layout: StemLayout,
        pulse_catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        catalog = pulse_catalogs[GeneratorClassName.PULSE_GENERATOR]
        bins = catalog.powers.shape[1]
        rows = [catalog.rows_by_instruction[HELD], catalog.rows_by_instruction[OTHER]]
        steady = SteadyHearing(layout=pulse_layout, catalogs=pulse_catalogs, bins=bins)
        heard = SequenceHearing.of(
            pulse_layout, pulse_catalogs, [_alone(bins), _alone(bins)], joint_matcher.candidate_provider
        )

        assert heard.powers(0, rows) == pytest.approx(steady.powers(0, rows))
        assert heard.unit_powers(1, rows) == pytest.approx(steady.unit_powers(1, rows))

    def test_the_neighbors_leak_stands_in_every_mix_before_any_row(
        self,
        pulse_layout: StemLayout,
        pulse_catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
        config: Config,
        extractor: FeatureExtractor,
    ) -> None:
        bins = pulse_catalogs[GeneratorClassName.PULSE_GENERATOR].powers.shape[1]
        fragment = rendered_fragment(config, extractor, {ChannelName.PULSE1: HELD})
        heard = SequenceHearing.of(
            pulse_layout,
            pulse_catalogs,
            [_alone(bins, leak=LEAK), _alone(bins, leak=LEAK)],
            joint_matcher.candidate_provider,
        )

        assert heard.empty_mix(fragment).power == pytest.approx(np.full(bins, 2 * LEAK))

    def test_a_proposed_note_is_heard_on_the_channel_whose_held_note_it_extends(
        self,
        pulse_layout: StemLayout,
        pulse_catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        catalog = pulse_catalogs[GeneratorClassName.PULSE_GENERATOR]
        bins = catalog.powers.shape[1]
        heard = SequenceHearing.of(
            pulse_layout, pulse_catalogs, [_alone(bins), _alone(bins, held=True)], joint_matcher.candidate_provider
        )

        kind = GeneratorClassName.PULSE_GENERATOR
        assert heard.place_of(kind, catalog.rows_by_instruction[HELD]) == 1
        assert heard.place_of(kind, catalog.rows_by_instruction[OTHER]) == 0
