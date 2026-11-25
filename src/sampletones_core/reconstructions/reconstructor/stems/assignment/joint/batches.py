from typing import List, Sequence

import numpy as np


def split_by_group(costs: np.ndarray, groups: Sequence[np.ndarray]) -> List[np.ndarray]:
    """The costs of ``groups`` of rows scored in one batch, cut back into one stretch per group.

    Scoring many groups' mixes in one call of the criterion costs far less than one call per group,
    so a choice among the rows of each group stacks them all, group after group, and reads its own
    stretch back here.

    Args:
        costs: One cost per row, the groups' rows in turn.
        groups: The groups of rows, in the order they were stacked.

    Returns:
        Each group's costs, in its rows' order.
    """
    bounds = np.cumsum([0, *[len(group) for group in groups]])
    return [costs[bounds[index] : bounds[index + 1]] for index in range(len(groups))]


def cheapest_row(rows: np.ndarray, costs: np.ndarray) -> int:
    """The row of ``rows`` at the lowest of ``costs``, the earlier of equally cheap ones."""
    return int(rows[int(np.argmin(costs))])
