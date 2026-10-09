from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.decoder.base import ChannelLattice

from .conftest import STEADY, per_frame_best, viterbi_decoder


class TestViterbiContinuity:
    def test_continuity_holds_a_steady_note_where_per_frame_choice_flickers(
        self,
        config: Config,
        flickering_frames: ChannelLattice,
    ) -> None:
        decoder = viterbi_decoder(config, pitch_weight=1.0)

        streams = decoder.decode({ChannelName.PULSE1: flickering_frames})
        chosen = [candidate.instruction for candidate in streams[ChannelName.PULSE1]]

        assert len(set(per_frame_best(flickering_frames))) > 1
        assert len(set(chosen)) == 1

    def test_zero_transition_weights_reduce_to_per_frame_choice(
        self,
        config: Config,
        flickering_frames: ChannelLattice,
    ) -> None:
        decoder = viterbi_decoder(
            config,
            pitch_weight=0.0,
            volume_weight=0.0,
            timbre_weight=0.0,
            on_off_weight=0.0,
        )

        streams = decoder.decode({ChannelName.PULSE1: flickering_frames})

        assert [candidate.instruction for candidate in streams[ChannelName.PULSE1]] == per_frame_best(flickering_frames)


class TestViterbiLatticeWidth:
    def test_reads_as_many_candidates_as_the_configured_shortlist(self, config: Config) -> None:
        assert viterbi_decoder(config).lattice_width == config.generation.decoder.top_k


class TestViterbiTransitionCost:
    def test_identical_instruction_has_no_cost(self, config: Config) -> None:
        decoder = viterbi_decoder(config)
        assert decoder._transition_cost(STEADY, STEADY) == 0.0

    def test_larger_pitch_jump_costs_more(self, config: Config) -> None:
        decoder = viterbi_decoder(config, pitch_weight=0.1)
        near = PulseInstruction(on=True, pitch=61, volume=10, duty_cycle=0)
        far = PulseInstruction(on=True, pitch=84, volume=10, duty_cycle=0)
        assert decoder._transition_cost(STEADY, near) < decoder._transition_cost(STEADY, far)

    def test_toggling_on_off_costs_the_on_off_weight(self, config: Config) -> None:
        decoder = viterbi_decoder(config, on_off_weight=0.25)
        silence = PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=0)
        assert decoder._transition_cost(STEADY, silence) == 0.25

    def test_a_resting_frame_costs_the_on_off_weight_to_reach(self, config: Config) -> None:
        """A rest is an off state, so a channel pays the same to fall silent as to start."""
        decoder = viterbi_decoder(config, on_off_weight=0.25)
        resting = PulseInstruction.null_instruction()
        assert decoder._transition_cost(STEADY, resting) == 0.25
        assert decoder._transition_cost(resting, resting) == 0.0
