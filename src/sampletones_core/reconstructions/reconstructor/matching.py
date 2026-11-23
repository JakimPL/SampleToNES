from dataclasses import dataclass
from typing import List, Sequence, Tuple

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
        cost: The frame's cost with this alternative sounding beside the stem's other picks, and the
            charge for breaking with the frames beside it where a neighbor pass charges one.
        contribution: What this alternative adds to the frame.
    """

    instruction: InstructionUnion
    cost: float
    contribution: Contribution


Column = Tuple[ScoredCandidate, ...]


@dataclass(frozen=True)
class RowsRequest:
    """
    Chosen candidates of one generator class, each to be scored beside what a mix sounds.

    Attributes:
        generator: The generator whose class the rows belong to.
        mix: What the stem's other channels sound in the frame.
        rows: The candidates, by their place in the class's candidates.
        powers: The power each candidate adds to the frame, read at ``drive``, one row per candidate.
        drive: The level the channel reaches for, which every candidate is read against.
    """

    generator: GeneratorUnion
    mix: FrameMix
    rows: Tuple[int, ...]
    powers: np.ndarray
    drive: float

    @property
    def mixed_powers(self) -> xp.ndarray:
        """The power of the frame with each row sounding beside the mix, one row per candidate."""
        return xp.asarray(self.powers) + xp.asarray(self.mix.power)


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

    A search settling its own shortlist hands the rows it kept (``score_rows``), and the rows of
    several channels are scored in one pass of the criterion (``score_requests``), each request
    reading its own stretch of the costs back. ``spectral_costs`` reads the first stage alone, which
    a search ranks its stacks of mixes by, and ``mix_costs`` the full cost of mixes sounding alone.
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
        spectral_costs = self.spectral_costs(target, unit_powers + xp.asarray(mix.power))
        shortlist = self._shortlist(spectral_costs, candidates, generator)
        request = RowsRequest(
            generator=generator,
            mix=mix,
            rows=tuple(shortlist),
            powers=np.asarray(to_numpy(unit_powers[xp.asarray(shortlist)]), dtype=np.float64),
            drive=drive,
        )
        return self._scored(target, [request], spectral_costs[shortlist])[0]

    def score_rows(
        self,
        target: Fragment,
        generator: GeneratorUnion,
        mix: FrameMix,
        rows: Sequence[int],
        *,
        drive: float,
    ) -> Column:
        """
        Score chosen candidates of one generator class with ``mix`` sounding, as a column is scored.

        A search that settles its own shortlist hands the rows it kept, by their place among the
        class's candidates, and each receives the full cost of the frame with it sounding at
        ``drive``, exactly as the shortlist of ``score_column`` does.

        Args:
            target: Target fragment to match.
            generator: The generator whose class the rows belong to.
            mix: What the stem's other picks sound in the frame.
            rows: The candidates scored, by their place in the class's candidates.
            drive: The level the channel reaches for, which every candidate is read against.

        Returns:
            The candidates with their frame costs, best first, silence ahead of an equal cost.
        """
        candidates = self.candidate_provider.candidates({generator.class_name(): generator})
        powers = np.asarray(to_numpy(_at_unit_drive(candidates.powers, drive)[xp.asarray(list(rows))]))
        request = RowsRequest(generator=generator, mix=mix, rows=tuple(rows), powers=powers, drive=drive)
        return self.score_requests(target, [request])[0]

    def score_requests(self, target: Fragment, requests: Sequence[RowsRequest]) -> List[Column]:
        """
        Score the chosen candidates of several channels in one pass, each as ``score_rows`` scores them.

        Args:
            target: Target fragment to match.
            requests: Each channel's class, mix, rows, their powers and drive.

        Returns:
            One column per request, in request order, each best first, silence ahead of an equal cost.
        """
        spectral_costs = self.spectral_costs(target, xp.concatenate([request.mixed_powers for request in requests]))
        return self._scored(target, requests, spectral_costs)

    def spectral_costs(self, target: Fragment, powers: xp.ndarray) -> np.ndarray:
        """The spectral cost of the frame with each row of ``powers`` sounding, the first stage of its cost.

        A row's features are read off its power as the library's are, so a stack of mixes ranks on
        the scale the library's candidates rank on.

        Args:
            target: Target fragment to match.
            powers: The power density per bin of each mix, one mix per row.

        Returns:
            One spectral cost per mix.
        """
        features = self.candidate_provider.features_of(xp.asarray(powers))
        return self.scorer.spectral_costs(target, features)

    def mix_cost(self, target: Fragment, mix: FrameMix) -> float:
        """The frame's cost with ``mix`` sounding alone, on the scale columns are scored on."""
        return float(self.mix_costs(target, [mix])[0])

    def mix_costs(self, target: Fragment, mixes: Sequence[FrameMix]) -> np.ndarray:
        """The frame's cost with each of ``mixes`` sounding alone, all scored in one pass."""
        spectral_costs = self.spectral_costs(target, np.stack([mix.power for mix in mixes]))
        return self._full_costs(target, spectral_costs, mixes)

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
                sounding=instruction.on,
            )

        if self.config.generation.calculation.find_best_phase:
            waveform = self.phase_aligner.align(residual, instruction, drive)
        else:
            waveform = self.candidate_provider.library_waveform(instruction) / drive

        return Contribution(power=power, expectation=waveform, variance=0.0, sounding=instruction.on)

    def _scored(self, target: Fragment, requests: Sequence[RowsRequest], spectral_costs: np.ndarray) -> List[Column]:
        """Each request's rows with the full cost of the frame each reaches beside its mix, best first.

        Every row of every request is scored in one pass of the criterion, request after request, in
        the order ``spectral_costs`` lists their spectral costs, and each request reads its own
        stretch of the costs back.
        """
        played = [self._played(request) for request in requests]
        contributions = [
            self._contributions(target, request, instructions) for request, instructions in zip(requests, played)
        ]
        costs = self._full_costs(target, spectral_costs, self._reached(requests, contributions))
        columns: List[Column] = []
        start = 0
        for instructions, added in zip(played, contributions):
            stop = start + len(added)
            columns.append(self._column(instructions, costs[start:stop], added))
            start = stop

        return columns

    def _played(self, request: RowsRequest) -> List[InstructionUnion]:
        """What each of the request's rows plays."""
        instructions = self.candidate_provider.candidates({request.generator.class_name(): request.generator})
        return [instructions.instructions[row] for row in request.rows]

    def _contributions(
        self, target: Fragment, request: RowsRequest, instructions: Sequence[InstructionUnion]
    ) -> List[Contribution]:
        """What each of the request's rows adds to the frame, against what its mix leaves of the frame's waveform."""
        residual = request.mix.residual_waveform(target)
        powers = np.asarray(request.powers, dtype=np.float64)
        return [
            self.contribution(instruction, residual, power, drive=request.drive)
            for instruction, power in zip(instructions, powers)
        ]

    @staticmethod
    def _reached(requests: Sequence[RowsRequest], contributions: Sequence[List[Contribution]]) -> List[FrameMix]:
        """The mix each row reaches: its request's mix with the row sounding in it, request after request."""
        reached: List[FrameMix] = []
        for request, added in zip(requests, contributions):
            reached.extend(request.mix.added(contribution) for contribution in added)

        return reached

    def _full_costs(self, target: Fragment, spectral_costs: np.ndarray, mixes: Sequence[FrameMix]) -> np.ndarray:
        """The full cost of the frame with each of ``mixes`` sounding, its spectral cost read beforehand."""
        return self.scorer.frame_costs(
            target,
            spectral_costs,
            np.stack([mix.expectation for mix in mixes]),
            np.array([mix.variance for mix in mixes]),
            np.array([mix.sounding for mix in mixes]),
        )

    @staticmethod
    def _column(
        instructions: Sequence[InstructionUnion], costs: np.ndarray, contributions: Sequence[Contribution]
    ) -> Column:
        """The rows at their costs, best first, silence ahead of an equal cost."""
        scored = [
            ScoredCandidate(instruction=instruction, cost=float(cost), contribution=contribution)
            for instruction, cost, contribution in zip(instructions, costs, contributions)
        ]
        return tuple(sorted(scored, key=FrameMatcher._rank))

    @staticmethod
    def _rank(candidate: ScoredCandidate) -> Tuple[float, bool]:
        """Where a candidate stands in its column: the cheaper first, and of equal costs the silent one first."""
        return candidate.cost, candidate.instruction.on

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
