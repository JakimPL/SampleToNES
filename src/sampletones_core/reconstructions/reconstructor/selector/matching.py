from dataclasses import dataclass
from typing import Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.generators import (
    GeneratorUnion,
    get_generator_by_instruction,
)
from sampletones_core.instructions import InstructionUnion

from ..approximation import ApproximationData
from ..candidates import CandidateProvider
from ..phase import PhaseAligner
from ..scorer import Scorer


@dataclass(frozen=True)
class ScoredCandidate:
    instruction: InstructionUnion
    cost: float
    approximation: Fragment


@dataclass(frozen=True)
class FrameMatcher:
    """
    Matches one target fragment against candidates of given generator classes.

    Carries the matching machinery the selectors and the stems assignment share: the
    two-stage criterion scoring, the winning channel's approximation, and the
    per-candidate approximation build.
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
        full ranking with the temporal term evaluated on each phase-aligned candidate.

        The shortlist ranks every candidate by the spectral term alone, which compares
        phase-averaged features and is therefore immune to how the candidate waveform
        happens to be phased. Each of the ``top_k`` shortlisted candidates is then built
        at its best phase against the target and receives the full criterion cost, so
        the temporal term measures waveform shape at the aligned phase. The aligned
        phase stands in for the rendered phase, which keeps oscillator continuity
        across frames.

        Args:
            fragment: Target fragment to match.
            remaining_generator_classes: Generators still available for this fragment.

        Returns:
            The shortlisted candidates with their aligned costs, best first.
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
            generator = get_generator_by_instruction(
                instruction,
                remaining_generator_classes,
            )
            approximation = self.build_approximation(
                fragment,
                instruction,
                generator,
            )
            cost = self.scorer.aligned_cost(
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

    def best_approximation(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> ApproximationData:
        """
        The winning channel's attribution, approximation, and instruction.

        Scores the candidates of the given generator classes and returns the best one
        as the channel it belongs to, its rendered approximation, and its instruction.
        """
        best = self.score_candidates(fragment, remaining_generator_classes)[0]
        generator = get_generator_by_instruction(
            best.instruction,
            remaining_generator_classes,
        )

        return ApproximationData(
            channel_name=ChannelName(generator.name),
            approximation=best.approximation,
            instruction=best.instruction,
        )

    def build_approximation(
        self,
        fragment: Fragment,
        instruction: InstructionUnion,
        generator: GeneratorUnion,
    ) -> Fragment:
        """
        Builds one candidate fragment for scoring: the phase-aligned waveform when
        best-phase search is enabled, or the generator's library approximation.
        """
        if self.config.generation.calculation.find_best_phase:
            return self.phase_aligner.align(fragment, instruction)

        return self.candidate_provider.get_approximation(
            instruction,
            generator,
        )
