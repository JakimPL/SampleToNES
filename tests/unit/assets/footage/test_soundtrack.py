from typing import Final

import numpy as np

from assets.footage.soundtrack import assembled, crossfade_phase

LENGTH: Final[int] = 400
CUT: Final[int] = 200
CROSSFADE: Final[int] = 20
EDGE_FADE: Final[int] = 10


class TestCrossfade:
    def test_the_rise_and_the_fall_keep_the_power_constant(self) -> None:
        phase = crossfade_phase(np.arange(LENGTH, dtype=np.float64), CUT, CROSSFADE)

        np.testing.assert_allclose(np.sin(phase) ** 2 + np.cos(phase) ** 2, 1.0)

    def test_the_crossfade_is_centered_on_the_cut(self) -> None:
        phase = crossfade_phase(np.arange(LENGTH, dtype=np.float64), CUT, CROSSFADE)

        assert phase[CUT - CROSSFADE // 2] == 0.0
        assert phase[CUT + CROSSFADE // 2] == np.pi / 2
        assert np.isclose(phase[CUT], np.pi / 4)


class TestAssembled:
    def test_each_piece_sounds_on_its_own_side_of_the_cut(self) -> None:
        first, second = np.full(LENGTH, 1.0), np.full(LENGTH, 2.0)

        sound = assembled(
            [(first, 0, CUT), (second, CUT, LENGTH)], length=LENGTH, crossfade=CROSSFADE, edge_fade=EDGE_FADE
        )

        assert sound[CUT - CROSSFADE] == 1.0
        assert sound[CUT + CROSSFADE] == 2.0

    def test_the_whole_fades_in_and_out(self) -> None:
        sound = assembled([(np.ones(LENGTH), 0, LENGTH)], length=LENGTH, crossfade=CROSSFADE, edge_fade=EDGE_FADE)

        assert sound[0] == 0.0
        assert sound[-1] == 0.0
        assert sound[LENGTH // 2] == 1.0
