from itertools import product
from pathlib import Path
from typing import Final, Iterator, List, Tuple

import pytest

from sampletones_application.logic.history.action import HistoryAction
from tests.suite.history.gestures import GESTURES_BY_LABEL, PAIR_KINDS, Gesture, attempt, perform
from tests.suite.history.session import HistorySession, history_session

PAIRS: Final[List[Tuple[HistoryAction, HistoryAction]]] = list(product(PAIR_KINDS, repeat=2))


def _pair_label(pair: Tuple[HistoryAction, HistoryAction]) -> str:
    return f"{pair[0]} then {pair[1]}"


@pytest.fixture(scope="module")
def shared_session(tmp_path_factory: pytest.TempPathFactory) -> Iterator[HistorySession]:
    """One application per worker, the every-part project opened afresh for each pair."""
    with history_session(tmp_path_factory.mktemp("pairs")) as opened:
        yield opened


def _pair(
    first: HistoryAction,
    second: HistoryAction,
) -> Tuple[Gesture, Gesture]:
    opening, repeating = PAIR_KINDS[second]
    return GESTURES_BY_LABEL[PAIR_KINDS[first][0]], GESTURES_BY_LABEL[repeating if first is second else opening]


class TestEveryPairOfActions:
    """Two gestures in a row, then every way back and forth, then a commit over the redo branch."""

    @pytest.mark.parametrize("pair", PAIRS, ids=_pair_label)
    def test_the_pair_restores_every_state(
        self,
        shared_session: HistorySession,
        pair: Tuple[HistoryAction, HistoryAction],
    ) -> None:
        session = shared_session
        session.reopen()
        first, second = _pair(*pair)

        perform(session, first)
        attempt(session, second)
        session.audit.walk()
        session.audit.jump_to(0)
        perform(session, second)

        assert session.history.cursor == 1
