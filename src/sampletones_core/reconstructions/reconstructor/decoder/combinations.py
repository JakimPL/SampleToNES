import itertools
from typing import Dict, List, Sequence, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.instructions import InstructionUnion

from .base import Alternatives, Decoder, Pool, StemPools, Streams
from .transition import TransitionWeights, transition_cost


class CombinationsDecoder(Decoder):
    """
    Plays the cheapest path through each stem's whole combinations, cost and continuity together.

    A path per channel weighs each of the channel's alternatives with the stem's other channels playing
    the frame's pick, so it cannot hold a line where only several channels changing together keep the
    frame cheap. Here a state is a whole combination of the stem's channels, its pulses in either order,
    and one path runs through the combinations the joint assignment pooled for every frame. A frame's
    cost counts once, as the criterion reads the frame, and a change between two frames costs what each
    channel pays for its own change. A move of one channel then trades the frame's cost against its
    change as a decoder of one channel at a time trades it, and a move of several channels together is
    weighed by the cost the frame reaches with all of them moved. A pulse holding its note through a note
    change, where the frame's cheapest combination would move it to another octave, then stays on its
    note.
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

        costs = _emissions(frames[0])
        backpointers: List[np.ndarray] = []
        for previous, current in itertools.pairwise(frames):
            totals = costs[:, np.newaxis] + self._transitions(previous, current)
            best = np.argmin(totals, axis=0)
            costs = totals[best, np.arange(len(current))] + _emissions(current)
            backpointers.append(best)

        last = int(np.argmin(costs))
        path = [last]
        for layer in reversed(backpointers):
            last = int(layer[last])
            path.append(last)

        path.reverse()
        return path

    def _transitions(self, previous: Pool, current: Pool) -> np.ndarray:
        """What moving from each combination of ``previous`` to each of ``current`` costs, channel by channel.

        A pool repeats a channel's few instructions across many combinations, so each channel's costs
        are reckoned once per pair of distinct instructions and spread over the combinations.
        """
        totals = np.zeros((len(previous), len(current)), dtype=np.float64)
        for position in range(len(current[0].candidates)):
            before, before_places = _distinct(
                [combination.candidates[position].instruction for combination in previous]
            )
            after, after_places = _distinct([combination.candidates[position].instruction for combination in current])
            costs = np.array(
                [[transition_cost(origin, destination, self.weights) for destination in after] for origin in before],
                dtype=np.float64,
            )
            totals += costs[np.ix_(before_places, after_places)]

        return totals


def _emissions(pool: Pool) -> np.ndarray:
    """Each combination's frame cost."""
    return np.array([combination.cost for combination in pool], dtype=np.float64)


def _distinct(instructions: Sequence[InstructionUnion]) -> Tuple[List[InstructionUnion], np.ndarray]:
    """The distinct instructions in first-seen order, and the place of each of ``instructions`` among them."""
    places: Dict[InstructionUnion, int] = {}
    indices = [places.setdefault(instruction, len(places)) for instruction in instructions]
    return list(places), np.array(indices, dtype=np.int64)
