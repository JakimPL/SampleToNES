from pathlib import Path
from typing import Iterator

import pytest

from tests.suite.history.session import HistorySession, history_session


@pytest.fixture
def session(tmp_path: Path) -> Iterator[HistorySession]:
    """The every-part project open in a headless application, its history held by the audit."""
    with history_session(tmp_path) as opened:
        yield opened
