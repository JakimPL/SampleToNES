from dataclasses import dataclass
from typing import Dict, List, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion

from .approximation import Approximation, WaveformApproximation
from .candidates import CandidateProvider
from .phase import PhaseAligner
from .scorer import Scorer


@dataclass(frozen=True)
class ScoredCandidate:
    instruction: InstructionUnion
    cost: float
    approximation: Approximation


Column = Tuple[ScoredCandidate, ...]


@dataclass(frozen=True)
class FrameMatcher:
    """
    Matches one target fragment against candidates of given generator classes.

    Carries the matching machinery the stems assignment works from: the two-stage criterion
    scoring and the per-candidate approximation build. What the scoring produces is a column
    of alternatives, which the assignment turns into ownership and the decoder into a stream.
    """

    config: Config
    candidate_provider: CandidateProvider
    scorer: Scorer
    phase_aligner: PhaseAligner

    @property
    def top_k(self) -> int:
        return self.config.generation.decoder.top_k

    def score_candidates(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> List[ScoredCandidate]:
        """
        Score candidates in two stages: a phase-independent spectral shortlist, then a
        full ranking with the temporal term each candidate's approximation measures.

        The shortlist ranks every candidate by the spectral term alone, which compares
        phase-averaged features and is therefore immune to how the candidate waveform
        happens to be phased. Each of the ``top_k`` shortlisted candidates then receives
        the full criterion cost. A candidate whose frames repeat one waveform shape is
        built at its best phase against the target, so the temporal term measures that
        shape, and the aligned phase stands in for the rendered phase. A candidate whose
        frames show different stretches of a sequence renders whatever stretch the channel
        has reached, so its temporal term is the loss expected over every phase.

        The shortlist is drawn by spectral rank, so scoring one generator class alone
        returns every candidate of that class that a wider scoring would have kept, and
        with it whichever of them the wider scoring picked.

        Args:
            fragment: Target fragment to match.
            remaining_generator_classes: Generators still available for this fragment.

        Returns:
            The shortlisted candidates with their full costs, best first.
        """
        valid_instructions, candidate_approximations = self.candidate_provider.candidates(remaining_generator_classes)
        spectral_costs = self.scorer.spectral_costs(
            fragment,
            candidate_approximations,
        )
        shortlist = Scorer.top_k(spectral_costs, self.top_k)

        scored: List[ScoredCandidate] = []
        for index in shortlist:
            instruction = valid_instructions[index]
            approximation = self.build_approximation(
                fragment,
                instruction,
            )
            cost = self.scorer.candidate_cost(
                fragment,
                float(spectral_costs[index]),
                approximation,
            )
            scored.append(
                ScoredCandidate(
                    instruction=instruction,
                    cost=cost,
                    approximation=approximation,
                )
            )

        scored.sort(key=lambda candidate: candidate.cost)
        return scored

    def reference_energy(self, fragment: Fragment) -> float:
        """How much sound a target holds, in the units the scoring measures its cost in."""
        return self.scorer.reference_energy(fragment)

    def build_approximation(
        self,
        fragment: Fragment,
        instruction: InstructionUnion,
    ) -> Approximation:
        """
        Builds one candidate's approximation for scoring.

        A candidate whose frames repeat one waveform shape is measured by that shape: at its
        best phase against the target when best-phase search is enabled, or as the generator's
        library approximation. A candidate whose frames show different stretches of a sequence
        is measured by its expected contribution, whatever the search setting.
        """
        library_fragment = self.candidate_provider.library_data[instruction]
        if not library_fragment.frames_share_shape(
            frame_length=self.config.library.frame_length,
            sample_rate=self.config.library.sample_rate,
        ):
            return self.candidate_provider.get_expected_approximation(instruction)

        if self.config.generation.calculation.find_best_phase:
            return WaveformApproximation(self.phase_aligner.align(fragment, instruction))

        return WaveformApproximation(self.candidate_provider.get_approximation(instruction))
