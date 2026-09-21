from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion
from sampletones_shared.array import to_numpy, xp

from .candidates import CandidateProvider, ClassCandidates
from .contribution import Contribution
from .mix import FrameMix
from .phase import PhaseAligner
from .scorer import Scorer


@dataclass(frozen=True)
class ScoredCandidate:
    """
    One alternative for a channel in one frame.

    Attributes:
        instruction: What the channel plays.
        cost: The frame's cost with this alternative sounding beside the stem's other picks.
        contribution: What this alternative adds to the frame.
    """

    instruction: InstructionUnion
    cost: float
    contribution: Contribution


Column = Tuple[ScoredCandidate, ...]


@dataclass(frozen=True)
class FrameMatcher:
    """
    Scores one channel's candidates in a target fragment with the stem's other picks sounding.

    Carries the matching machinery the stems assignment works from: the two-stage criterion
    scoring and the per-candidate contribution build. What the scoring produces is a column of
    alternatives on one scale, the channel's silence among them, which the assignment turns into
    ownership and the decoder into a stream. A drive lifts what a channel reaches for: every
    candidate is read at unit drive, so the row fitting the target is the one sounding it at the
    drive, and a channel is answered at the level its own recording is given.
    """

    config: Config
    candidate_provider: CandidateProvider
    scorer: Scorer
    phase_aligner: PhaseAligner

    @property
    def top_k(self) -> int:
        return self.config.generation.decoder.top_k

    def score_column(
        self,
        target: Fragment,
        generator: GeneratorUnion,
        mix: FrameMix,
        *,
        drive: float,
    ) -> Column:
        """
        Score one generator class's candidates in two stages, each added to ``mix``.

        Every candidate is read at unit drive: its waveform divides by the drive and its power
        by the drive's square, so a rising drive reaches for a louder row and settles on the
        loudest the class holds. Each candidate's power is added to the mix and the result
        ranked by the spectral term, which compares phase-averaged powers and is therefore
        immune to how the waveforms happen to be phased. The ``top_k`` best and the class's silent instruction
        then receive the full cost of the frame with them sounding. A candidate whose frames
        repeat one waveform shape adds its rendering at its best phase against what the mix
        leaves of the target's waveform, or its library sample from the start when best-phase
        search is off. A candidate whose frames show different stretches of a sequence adds its
        mean level and its variance.

        Args:
            target: Target fragment to match.
            generator: The generator whose class is scored.
            mix: What the stem's other picks sound in the frame.
            drive: The level the channel reaches for, which every candidate is read against.

        Returns:
            The shortlisted candidates with their frame costs, best first, silence ahead of an
            equal cost.

        Raises:
            ValueError: If the library lacks the class's silent instruction.
        """
        candidates = self.candidate_provider.candidates({generator.class_name(): generator})
        unit_powers = _at_unit_drive(candidates.powers, drive)
        mixed = self.candidate_provider.features_of(unit_powers + xp.asarray(mix.power))
        spectral_costs = self.scorer.spectral_costs(target, mixed)
        shortlist = self._shortlist(spectral_costs, candidates, generator)

        residual = mix.residual_waveform(target)
        powers = np.asarray(to_numpy(unit_powers[xp.asarray(shortlist)]), dtype=np.float64)
        contributions = [
            self.contribution(candidates.instructions[index], residual, power, drive=drive)
            for index, power in zip(shortlist, powers)
        ]
        costs = self.scorer.frame_costs(
            target,
            spectral_costs[shortlist],
            np.stack([mix.expectation + contribution.expectation for contribution in contributions]),
            np.array([mix.variance + contribution.variance for contribution in contributions]),
        )
        scored = [
            ScoredCandidate(instruction=candidates.instructions[index], cost=float(cost), contribution=contribution)
            for index, cost, contribution in zip(shortlist, costs, contributions)
        ]
        scored.sort(key=lambda candidate: (candidate.cost, candidate.instruction.on))
        return tuple(scored)

    def mix_cost(self, target: Fragment, mix: FrameMix) -> float:
        """The frame's cost with ``mix`` sounding alone, on the scale columns are scored on."""
        features = self.candidate_provider.features_of(xp.asarray(mix.power)[None, :])
        spectral_costs = self.scorer.spectral_costs(target, features)
        costs = self.scorer.frame_costs(target, spectral_costs, mix.expectation[None, :], np.array([mix.variance]))
        return float(costs[0])

    def reference_energy(self, fragment: Fragment) -> float:
        """How much sound a target holds, in the units the scoring measures its cost in."""
        return self.scorer.reference_energy(fragment)

    def contribution(
        self,
        instruction: InstructionUnion,
        residual: np.ndarray,
        power: np.ndarray,
        *,
        drive: float,
    ) -> Contribution:
        """
        What one candidate adds to a frame whose waveform the mix leaves as ``residual``.

        Args:
            instruction: The candidate.
            residual: What the frame's waveform holds beyond the stem's other picks.
            power: The candidate's power density per bin, read at unit drive.
            drive: The level the channel reaches for, which the candidate's waveform and mean
                level divide by, and its variance the drive's square.

        Returns:
            Contribution: The candidate's power, expected waveform and variance.
        """
        library_fragment = self.candidate_provider.library_data[instruction]
        if not library_fragment.frames_share_shape(
            frame_length=self.config.library.frame_length,
            sample_rate=self.config.library.sample_rate,
        ):
            mean, variance = self.candidate_provider.expected_moments(instruction)
            return Contribution(
                power=power,
                expectation=np.full(residual.shape[0], mean / drive),
                variance=variance / drive**2,
            )

        if self.config.generation.calculation.find_best_phase:
            waveform = self.phase_aligner.align(residual, instruction, drive)
        else:
            waveform = self.candidate_provider.library_waveform(instruction) / drive

        return Contribution(power=power, expectation=waveform, variance=0.0)

    def _shortlist(
        self,
        spectral_costs: np.ndarray,
        candidates: ClassCandidates,
        generator: GeneratorUnion,
    ) -> List[int]:
        """The ``top_k`` best spectral costs, with the class's silence among them.

        Raises:
            ValueError: If the library lacks the class's silent instruction.
        """
        silence = generator.get_instruction_type().null_instruction()
        if silence not in candidates.instructions:
            raise ValueError(f"The library lacks the silent instruction of {generator.class_name()}")

        shortlist = [int(index) for index in Scorer.top_k(spectral_costs, self.top_k)]
        silent_index = candidates.instructions.index(silence)
        if silent_index not in shortlist:
            shortlist.append(silent_index)

        return shortlist


def _at_unit_drive(powers: xp.ndarray, drive: float) -> xp.ndarray:
    """The candidates' powers read at unit drive, which a power divides by the drive's square."""
    if drive == UNIT_DRIVE:
        return powers

    return powers / drive**2


def column_of(scored: Column, width: int) -> Column:
    """
    The alternatives a decoder reading ``width`` of them chooses among.

    A column wider than one keeps the channel's silence, standing in for the last kept
    alternative when the silence ranks below them, so a decoder can always rest the channel.

    Args:
        scored: A column best first.
        width: How many alternatives the decoder reads.

    Returns:
        Column: The best ``width`` alternatives.
    """
    kept = scored[:width]
    if width == 1 or any(not candidate.instruction.on for candidate in kept):
        return kept

    silence = next((candidate for candidate in scored if not candidate.instruction.on), None)
    if silence is None:
        return kept

    return (*kept[:-1], silence)
