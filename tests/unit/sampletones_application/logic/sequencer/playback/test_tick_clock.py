from fractions import Fraction
from typing import Final, Tuple

import numpy as np
import pytest

from sampletones_application.constants.playback import MAX_TICKS_PER_ROW, MIN_TICKS_PER_ROW
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.timing import Metre, RowRate, TickClock, calculate_groove
from tests.suite.base import BaseTestSuite
from tests.unit.sampletones_application.logic.sequencer.playback.conftest import (
    add_sample,
    all_channels,
    make_controller,
    make_pulse_reconstruction,
    place_row,
)

UNEVEN_SAMPLE_RATE: Final[int] = 22050
EVEN_SAMPLE_RATE: Final[int] = 44100
UNEVEN_RATES: Final[Tuple[int, ...]] = (8000, 16000, 22050)


def _config(sample_rate: int) -> Config:
    config = Config()
    return config.model_copy(update={"library": config.library.model_copy(update={"sample_rate": sample_rate})})


def _expected_ticks(controller: ProjectController) -> Tuple[int, ...]:
    settings = controller.project.settings
    return calculate_groove(
        RowRate.from_settings(settings),
        Metre.from_settings(settings, rows=controller.project.song.rows_per_pattern),
        minimum_ticks=MIN_TICKS_PER_ROW,
        maximum_ticks=MAX_TICKS_PER_ROW,
    ).ticks


class TestRowsFollowTheTickClock(BaseTestSuite):
    """A rendered row spans the samples its ticks span, so the groove's tempo is the tempo heard."""

    @pytest.mark.parametrize("sample_rate", UNEVEN_RATES + (EVEN_SAMPLE_RATE, 48000))
    def test_a_pattern_spans_its_exact_duration(self, sample_rate: int) -> None:
        controller = make_controller()
        synthesizer = RowSynthesizer(controller, _config(sample_rate), active_channels=all_channels)
        ticks = _expected_ticks(controller)

        rendered = sum(len(synthesizer.render_row()[0]) for _ in range(len(ticks)))

        clock = TickClock.from_parameters(
            sample_rate=sample_rate,
            nes_frequency=controller.project.settings.nes_frequency,
        )
        assert rendered == clock.samples_at(sum(ticks))

    @pytest.mark.parametrize("sample_rate", UNEVEN_RATES)
    def test_a_long_run_does_not_drift(self, sample_rate: int) -> None:
        """The property a fixed rounded frame length loses: the error stays below one sample."""
        controller = make_controller()
        synthesizer = RowSynthesizer(controller, _config(sample_rate), active_channels=all_channels)
        ticks = _expected_ticks(controller)
        patterns = 40

        rendered = 0
        for _ in range(patterns):
            synthesizer.set_position(0, 0)
            rendered += sum(len(synthesizer.render_row()[0]) for _ in range(len(ticks)))

        exact = Fraction(sample_rate, controller.project.settings.nes_frequency) * sum(ticks) * patterns
        assert abs(rendered - exact) < 1

    def test_a_row_spans_the_sum_of_its_ticks(self) -> None:
        controller = make_controller()
        synthesizer = RowSynthesizer(
            controller,
            _config(UNEVEN_SAMPLE_RATE),
            active_channels=all_channels,
        )
        clock = TickClock.from_parameters(
            sample_rate=UNEVEN_SAMPLE_RATE,
            nes_frequency=controller.project.settings.nes_frequency,
        )
        ticks = _expected_ticks(controller)

        elapsed = 0
        for row_ticks in ticks:
            chunk, _ = synthesizer.render_row()
            expected = clock.samples_at(elapsed + row_ticks) - clock.samples_at(elapsed)
            assert len(chunk) == expected
            elapsed += row_ticks

    def test_rows_vary_in_length_where_their_ticks_straddle_a_sample(self) -> None:
        """The variation is the mechanism; a run of identical lengths would mean the drift is back.

        An odd tick count is what makes it visible at the row: five ticks of 367.5 samples span
        1837.5, so consecutive rows take the floor and the ceiling in turn.
        """
        controller = make_controller()
        controller.set_speed(5)
        synthesizer = RowSynthesizer(
            controller,
            _config(UNEVEN_SAMPLE_RATE),
            active_channels=all_channels,
        )
        lengths = {len(synthesizer.render_row()[0]) for _ in range(len(_expected_ticks(controller)))}
        assert lengths == {1837, 1838}

    def test_reset_returns_the_clock_to_the_first_tick(self) -> None:
        controller = make_controller()
        synthesizer = RowSynthesizer(
            controller,
            _config(UNEVEN_SAMPLE_RATE),
            active_channels=all_channels,
        )
        first = len(synthesizer.render_row()[0])

        synthesizer.set_position(0, 0)
        synthesizer.reset()

        assert len(synthesizer.render_row()[0]) == first

    def test_a_frequency_change_rebuilds_the_clock(self) -> None:
        controller = make_controller()
        synthesizer = RowSynthesizer(controller, _config(EVEN_SAMPLE_RATE), active_channels=all_channels)

        controller.set_nes_frequency(60)
        synthesizer.render_row()
        controller.set_nes_frequency(30)
        synthesizer.set_position(0, 0)
        synthesizer.reset()
        ticks = _expected_ticks(controller)

        rendered = sum(len(synthesizer.render_row()[0]) for _ in range(len(ticks)))
        clock = TickClock.from_parameters(sample_rate=EVEN_SAMPLE_RATE, nes_frequency=30)
        assert rendered == clock.samples_at(sum(ticks))


class TestChannelsFillTheRow(BaseTestSuite):
    """Every channel writes into the same tick boundaries, so a mix never leaves a gap."""

    def test_a_sounding_channel_fills_every_tick(self) -> None:
        controller = make_controller()
        reconstruction = make_pulse_reconstruction(count=1)
        sample = add_sample(controller, reconstruction, loop=True)
        place_row(controller, generator=GeneratorName.PULSE1, row_index=0, sample_id=sample.id)
        synthesizer = RowSynthesizer(
            controller,
            _config(UNEVEN_SAMPLE_RATE),
            active_channels=all_channels,
        )

        chunk, _ = synthesizer.render_row()

        assert np.any(chunk != 0.0)
        assert not np.any(np.isnan(chunk))

    def test_a_sounding_note_stays_continuous_across_a_tick_length_change(self) -> None:
        """A tick of a different length resumes the oscillator where the last one ended."""
        controller = make_controller()
        reconstruction = make_pulse_reconstruction(count=1)
        sample = add_sample(controller, reconstruction, loop=True)
        place_row(controller, generator=GeneratorName.PULSE1, row_index=0, sample_id=sample.id)
        synthesizer = RowSynthesizer(
            controller,
            _config(UNEVEN_SAMPLE_RATE),
            active_channels=all_channels,
        )

        chunk, _ = synthesizer.render_row()
        steps = np.abs(np.diff(chunk))

        assert float(steps.max()) <= 1.0
