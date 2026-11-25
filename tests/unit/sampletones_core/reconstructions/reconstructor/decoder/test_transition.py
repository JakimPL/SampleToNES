import pytest

from sampletones_core.configs import Config
from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.decoder.transition import TransitionWeights, transition_cost

from .conftest import STEADY

WEIGHTS = TransitionWeights(pitch=0.1, volume=0.01, timbre=0.05, on_off=0.25)
FREE = TransitionWeights(pitch=0.0, volume=0.0, timbre=0.0, on_off=0.0)


class TestTransitionWeights:
    def test_the_weights_are_the_decoder_settings(self, config: Config) -> None:
        decoder = config.generation.decoder

        weights = TransitionWeights.of(config)

        assert (weights.pitch, weights.volume, weights.timbre, weights.on_off) == (
            decoder.pitch_weight,
            decoder.volume_weight,
            decoder.timbre_weight,
            decoder.on_off_weight,
        )


class TestTransitionCost:
    def test_identical_instruction_has_no_cost(self) -> None:
        assert transition_cost(STEADY, STEADY, WEIGHTS) == 0.0

    def test_larger_pitch_jump_costs_more(self) -> None:
        near = PulseInstruction(on=True, pitch=61, volume=10, duty_cycle=0)
        far = PulseInstruction(on=True, pitch=84, volume=10, duty_cycle=0)

        assert transition_cost(STEADY, near, WEIGHTS) < transition_cost(STEADY, far, WEIGHTS)

    def test_toggling_on_off_costs_the_on_off_weight(self) -> None:
        silence = PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=0)

        assert transition_cost(STEADY, silence, WEIGHTS) == WEIGHTS.on_off

    def test_a_resting_frame_costs_the_on_off_weight_to_reach(self) -> None:
        """A rest is an off state, so a channel pays the same to fall silent as to start."""
        resting = PulseInstruction.null_instruction()

        assert transition_cost(STEADY, resting, WEIGHTS) == WEIGHTS.on_off
        assert transition_cost(resting, STEADY, WEIGHTS) == WEIGHTS.on_off
        assert transition_cost(resting, resting, WEIGHTS) == 0.0

    def test_a_pulse_pays_for_its_pitch_its_volume_and_its_duty_cycle(self) -> None:
        moved = PulseInstruction(on=True, pitch=STEADY.pitch + 2, volume=STEADY.volume - 3, duty_cycle=2)

        assert transition_cost(STEADY, moved, WEIGHTS) == pytest.approx(
            2 * WEIGHTS.pitch + 3 * WEIGHTS.volume + WEIGHTS.timbre
        )

    def test_the_triangle_pays_for_its_pitch_alone(self) -> None:
        low = TriangleInstruction(on=True, pitch=40)
        high = TriangleInstruction(on=True, pitch=45)

        assert transition_cost(low, high, WEIGHTS) == pytest.approx(5 * WEIGHTS.pitch)

    def test_the_noise_pays_for_its_period_its_volume_and_its_mode(self) -> None:
        before = NoiseInstruction(on=True, period=4, volume=10, short=False)
        after = NoiseInstruction(on=True, period=7, volume=8, short=True)

        assert transition_cost(before, after, WEIGHTS) == pytest.approx(
            3 * WEIGHTS.pitch + 2 * WEIGHTS.volume + WEIGHTS.timbre
        )

    def test_two_silent_frames_cost_nothing_whatever_their_fields_hold(self) -> None:
        """A silent instruction sounds nothing, so the note, volume and timbre it carries go unheard."""
        low = PulseInstruction(on=False, pitch=40, volume=0, duty_cycle=0)
        high = PulseInstruction(on=False, pitch=80, volume=12, duty_cycle=3)

        assert transition_cost(low, high, WEIGHTS) == 0.0

    def test_a_channel_starting_pays_the_on_off_weight_alone_however_far_its_silence_lies(self) -> None:
        far_silence = PulseInstruction(on=False, pitch=STEADY.pitch + 24, volume=0, duty_cycle=3)

        assert transition_cost(far_silence, STEADY, WEIGHTS) == WEIGHTS.on_off
        assert transition_cost(STEADY, far_silence, WEIGHTS) == WEIGHTS.on_off

    @pytest.mark.parametrize("duty_cycle", [1, 3], ids=["the_next_duty_cycle", "the_farthest_duty_cycle"])
    def test_a_change_of_timbre_costs_the_timbre_weight_however_far_it_goes(self, duty_cycle: int) -> None:
        changed = PulseInstruction(on=True, pitch=STEADY.pitch, volume=STEADY.volume, duty_cycle=duty_cycle)

        assert transition_cost(STEADY, changed, WEIGHTS) == WEIGHTS.timbre

    def test_free_weights_charge_no_change(self) -> None:
        moved = PulseInstruction(on=True, pitch=STEADY.pitch + 12, volume=STEADY.volume - 5, duty_cycle=3)
        silence = PulseInstruction.null_instruction()

        assert transition_cost(STEADY, moved, FREE) == 0.0
        assert transition_cost(STEADY, silence, FREE) == 0.0

    def test_instructions_of_two_kinds_of_channel_are_refused(self) -> None:
        with pytest.raises(TypeError, match="one kind"):
            transition_cost(STEADY, TriangleInstruction(on=True, pitch=60), WEIGHTS)
