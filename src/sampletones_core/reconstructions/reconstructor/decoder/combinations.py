import itertools
from typing import Dict, List, Sequence, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.instructions import InstructionUnion

from .base import Alternatives, Decoder, Pool, StemPools, Streams
from .path import traced_back
from .transition import TransitionWeights, transition_cost


class CombinationsDecoder(Decoder):
    """
    Plays the cheapest path through each stem's whole combinations, cost and continuity together.

    A path per channel weighs each of the channel's alternatives with the stem's other channels playing
    the frame's pick, so it holds a line only where one channel changing alone keeps the frame cheap.
    Here a state is a whole combination of the stem's channels, its pulses in either order, and one
    path runs through the combinations the joint assignment pooled for every frame. A path costs:

    - each frame's cost with its combination sounding, counted once, as the criterion reads the frame;
    - between two frames, what each channel pays for its own change, as the Viterbi decoder charges it.

    A move of one channel then trades the frame's cost against its change as a decoder of one channel
    at a time trades it, and a move of several channels together is weighed by the cost the frame
    reaches with all of them moved. A pulse holding its note through a note change, where the frame's
    cheapest combination would move it to another octave, then stays on its note. A tie goes to the
    earlier combination of a pool, as the Viterbi decoder's goes to the earlier candidate of a column.

    The pools name the channels each stem's path decides, and the lattices name the channels in play
    and the order the streams follow.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.weights = TransitionWeights.of(config)

    @property
    def lattice_width(self) -> int:
        return self.config.generation.decoder.top_k

    def decode(self, alternatives: Alternatives) -> Streams:
        """Every channel's stream, read off the path its stem's combinations take.

        Raises:
            ValueError: If a channel in play belongs to no stem's pools.
        """
        streams: Streams = {}
        for stem_pools in alternatives.pools.values():
            streams.update(self._decode_stem(stem_pools))

        unpooled = [channel_name for channel_name in alternatives.lattices if channel_name not in streams]
        if unpooled:
            raise ValueError(f"The combinations decoder needs every channel in a stem's pools; {unpooled} has none")

        return {channel_name: streams[channel_name] for channel_name in alternatives.lattices}

    def _decode_stem(self, stem_pools: StemPools) -> Streams:
        """The stem's channels, each playing its part of the combination the path takes in every frame."""
        path = self._path(stem_pools)
        return {
            channel_name: [pool[state].candidates[position] for pool, state in zip(stem_pools.frames, path)]
            for position, channel_name in enumerate(stem_pools.channel_names)
        }

    def _path(self, stem_pools: StemPools) -> List[int]:
        """The combination the cheapest path takes in every frame, by its place in the frame's pool."""
        frames = stem_pools.frames
        if not frames:
            return []

        costs = self._emissions(frames[0])
        backpointers: List[List[int]] = []
        for previous, current in itertools.pairwise(frames):
            costs, best = self._step(costs, previous, current)
            backpointers.append(best)

        return traced_back(backpointers, costs.tolist())

    def _step(self, costs: np.ndarray, previous: Pool, current: Pool) -> Tuple[np.ndarray, List[int]]:
        """The cheapest path to each combination of ``current``, and the combination of ``previous`` it comes from.

        Args:
            costs: What the cheapest path to each combination of ``previous`` costs.
            previous: The pool of the frame before.
            current: The pool of the frame.

        Returns:
            What the cheapest path to each combination of ``current`` costs, its own frame's cost
            included, and the place in ``previous`` of the combination it comes from, the earliest of
            equally cheap ones.
        """
        totals = costs[:, np.newaxis] + self._transitions(previous, current)
        best = np.argmin(totals, axis=0)
        return totals[best, np.arange(len(current))] + self._emissions(current), best.tolist()

    def _transitions(self, previous: Pool, current: Pool) -> np.ndarray:
        """What moving from each combination of ``previous`` to each of ``current`` costs, summed over the channels."""
        totals = np.zeros((len(previous), len(current)), dtype=np.float64)
        for position in range(len(current[0].candidates)):
            totals += self._channel_transitions(previous, current, position)

        return totals

    def _channel_transitions(self, previous: Pool, current: Pool, position: int) -> np.ndarray:
        """What the channel at ``position`` pays to move from each combination of ``previous`` to each of ``current``.

        A pool repeats a channel's few instructions across many combinations, so the channel's costs
        are reckoned once per pair of distinct instructions and spread over the combinations.
        """
        before, before_places = self._distinct(self._played(previous, position))
        after, after_places = self._distinct(self._played(current, position))
        costs = np.array(
            [[transition_cost(origin, destination, self.weights) for destination in after] for origin in before],
            dtype=np.float64,
        )
        spread: np.ndarray = costs[np.ix_(before_places, after_places)]
        return spread

    @staticmethod
    def _emissions(pool: Pool) -> np.ndarray:
        """Each combination's frame cost, which the frame counts once whatever the channels it sounds."""
        return np.array([combination.cost for combination in pool], dtype=np.float64)

    @staticmethod
    def _played(pool: Pool, position: int) -> List[InstructionUnion]:
        """What the channel at ``position`` plays in each combination of ``pool``."""
        return [combination.candidates[position].instruction for combination in pool]

    @staticmethod
    def _distinct(instructions: Sequence[InstructionUnion]) -> Tuple[List[InstructionUnion], np.ndarray]:
        """The distinct instructions in first-seen order, and the place of each of ``instructions`` among them."""
        places: Dict[InstructionUnion, int] = {}
        indices = [places.setdefault(instruction, len(places)) for instruction in instructions]
        return list(places), np.array(indices, dtype=np.int64)
