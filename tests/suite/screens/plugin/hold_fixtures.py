import os
from pathlib import Path
from typing import Final

import pytest

from tests.suite.screens.environment import ARTIFACTS_VARIABLE
from tests.suite.screens.holds.base import Holds
from tests.suite.screens.holds.conversion import ConversionHold
from tests.suite.screens.holds.export import ExportHold
from tests.suite.screens.holds.regeneration import RegenerationHold
from tests.suite.screens.holds.scan import ScanHold
from tests.suite.screens.holds.signal import ReleaseSignal

CONVERSION_RELEASE_FILE: Final[str] = "release-conversion"
SCAN_RELEASE_FILE: Final[str] = "release-scan"
SCAN_ENTRY_SECONDS: Final[float] = 0.05


@pytest.fixture
def screen_holds() -> Holds:
    """The work the scenario holds under way, let go before it leaves."""
    return Holds()


@pytest.fixture
def conversion_hold(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> ConversionHold:
    """Holds every conversion the scenario starts halfway through matching, until the scenario releases it."""
    hold = ConversionHold(ReleaseSignal(Path(os.environ[ARTIFACTS_VARIABLE]) / CONVERSION_RELEASE_FILE))
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold


@pytest.fixture
def scan_hold(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> ScanHold:
    """Holds every folder scan the scenario starts once its tree is read, until the scenario releases it."""
    hold = ScanHold(
        ReleaseSignal(Path(os.environ[ARTIFACTS_VARIABLE]) / SCAN_RELEASE_FILE),
        interval=SCAN_ENTRY_SECONDS,
    )
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold


@pytest.fixture
def regeneration_hold(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> RegenerationHold:
    """Holds every rebuild an edit of a channel asks for, until the scenario releases it."""
    hold = RegenerationHold()
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold


@pytest.fixture
def export_hold(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> ExportHold:
    """Holds every export at its first report, until the scenario releases it."""
    hold = ExportHold()
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold
