from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.decoder.base import Alternatives, ChannelLattice

from .conftest import STEADY, per_frame_best, viterbi_decoder


class TestViterbiContinuity:
    def test_continuity_holds_a_steady_note_where_per_frame_choice_flickers(
        self,
        config: Config,
        flickering_frames: ChannelLattice,
    ) -> None:
        decoder = viterbi_decoder(config, pitch_weight=1.0)

        streams = decoder.decode(Alternatives(lattices={ChannelName.PULSE1: flickering_frames}, pools={}))
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

        streams = decoder.decode(Alternatives(lattices={ChannelName.PULSE1: flickering_frames}, pools={}))

        assert [candidate.instruction for candidate in streams[ChannelName.PULSE1]] == per_frame_best(flickering_frames)


class TestViterbiLatticeWidth:
    def test_reads_as_many_candidates_as_the_configured_shortlist(self, config: Config) -> None:
        assert viterbi_decoder(config).lattice_width == config.generation.decoder.top_k
