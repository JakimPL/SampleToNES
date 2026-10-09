from typing import Dict, List, Optional, Sequence, Set

NO_BEND: int = 0


def smoothed(
    proposals: Sequence[Optional[int]],
    *,
    window: int,
    change_weight: float,
) -> List[int]:
    """One bend per frame, following the readings while paying for every change it makes.

    A reading is made frame by frame and a frame's own reading is the best statement of where its
    note sits, but a bend that follows every reading exactly jitters, and jitter is more audible
    than the tuning error it chases. So the walk weighs the distance from each frame's reading
    against a toll on changing at all, and settles on the run of bends that costs least over the
    whole stream — the same shape the decoder settles a note contour with.

    The states a frame may take are the readings its neighborhood proposed, together with no bend
    at all. Drawing them from the readings is what keeps the walk small: the divider range a note
    owns spans tens of steps at the bottom of the range, while the readings around any one frame
    are a handful.

    Args:
        proposals: The bend each frame's reading asks for, ``None`` where it made none.
        window: The frames on either side whose readings a frame may settle on.
        change_weight: The divider steps of reading error worth avoiding one change.

    Returns:
        List[int]: The bend each frame writes.
    """
    if not proposals:
        return []

    states = [_states(proposals, frame, window) for frame in range(len(proposals))]
    costs: Dict[int, float] = {bend: _reading_cost(bend, proposals[0]) for bend in states[0]}
    origins: List[Dict[int, int]] = []

    for frame in range(1, len(proposals)):
        step: Dict[int, float] = {}
        origin: Dict[int, int] = {}
        for bend in states[frame]:
            previous = _cheapest_predecessor(costs, bend, change_weight)
            step[bend] = (
                costs[previous] + (0.0 if previous == bend else change_weight) + _reading_cost(bend, proposals[frame])
            )
            origin[bend] = previous

        costs = step
        origins.append(origin)

    return _walked_back(costs, origins)


def _cheapest_predecessor(costs: Dict[int, float], bend: int, change_weight: float) -> int:
    """The bend a frame is cheapest to arrive at ``bend`` from, holding costing nothing."""
    reached = {held: cost + (0.0 if held == bend else change_weight) for held, cost in costs.items()}
    return min(reached, key=lambda held: reached[held])


def _states(proposals: Sequence[Optional[int]], frame: int, window: int) -> List[int]:
    """The bends a frame may settle on: what its neighborhood read, and no bend at all."""
    opening = max(0, frame - window)
    closing = min(len(proposals), frame + window + 1)
    nearby: Set[int] = {proposal for proposal in proposals[opening:closing] if proposal is not None}
    nearby.add(NO_BEND)
    return sorted(nearby)


def _reading_cost(bend: int, proposal: Optional[int]) -> float:
    """How far a bend stands from what the frame read, and nothing where it read nothing."""
    if proposal is None:
        return 0.0

    return float(abs(bend - proposal))


def _walked_back(costs: Dict[int, float], origins: List[Dict[int, int]]) -> List[int]:
    """The least-cost run of bends, read back from the frame it ended on."""
    bend = min(costs, key=lambda held: costs[held])
    walked = [bend]
    for origin in reversed(origins):
        bend = origin[bend]
        walked.append(bend)

    return list(reversed(walked))
