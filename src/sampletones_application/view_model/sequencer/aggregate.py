from typing import Set

from sampletones_shared.constants.symbols import MIXED
from sampletones_shared.utils.agreement import Agreement


def aggregate_labels(values: Set[str], *, default: str) -> str:
    """Collapses a set of pre-formatted cell labels into one summary label.

    Used by the master row/column of both sequencer grids: an empty set yields the
    ``default`` (no relevant cells), a single shared value is shown verbatim, and
    any disagreement collapses to :data:`MIXED`.
    """
    return Agreement.collapse(values).resolve(absent=default, mixed=MIXED)
