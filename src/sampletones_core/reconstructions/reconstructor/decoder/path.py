from typing import List, Sequence

import numpy as np


def traced_back(backpointers: Sequence[Sequence[int]], final_costs: Sequence[float]) -> List[int]:
    """The cheapest path's state in every frame, traced back from the cheapest state of the last frame.

    A forward pass keeps, for every state of every frame after the first, the state of the frame
    before that reaches it cheapest. The cheapest last state ends the path, the earliest of equally
    cheap ones, so of two paths costing the same the one through the earlier state stands, as a
    column lists the silence ahead of an equal cost.

    Args:
        backpointers: For every frame after the first, each state's cheapest predecessor.
        final_costs: What the cheapest path to each state of the last frame costs.

    Returns:
        The state the path takes in every frame, first to last, by its place in its frame.
    """
    last = int(np.argmin(final_costs))
    path = [last]
    for layer in reversed(backpointers):
        last = int(layer[last])
        path.append(last)

    path.reverse()
    return path
