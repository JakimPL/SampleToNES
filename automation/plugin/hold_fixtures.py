import os
from pathlib import Path
from typing import Final

import pytest

from automation.environment import ARTIFACTS_VARIABLE
from automation.holds.base import Holds
from automation.holds.conversion import ConversionHold
from automation.holds.export import ExportHold
from automation.holds.regeneration import RegenerationHold
from automation.holds.scan import ScanHold
from automation.holds.signal import ReleaseSignal

CONVERSION_RELEASE_FILE: Final[str] = "release-conversion"
SCAN_RELEASE_FILE: Final[str] = "release-scan"
SCAN_ENTRY_SECONDS: Final[float] = 0.05


@pytest.fixture(name="screen_holds")
def screen_holds_fixture() -> Holds:
    """The work the scenario holds under way, let go before it leaves."""
    return Holds()


@pytest.fixture(name="conversion_hold")
def conversion_hold_fixture(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> ConversionHold:
    """Holds every conversion the scenario starts halfway through matching, until the scenario releases it."""
    hold = ConversionHold(ReleaseSignal(Path(os.environ[ARTIFACTS_VARIABLE]) / CONVERSION_RELEASE_FILE))
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold


@pytest.fixture(name="scan_hold")
def scan_hold_fixture(
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


@pytest.fixture(name="regeneration_hold")
def regeneration_hold_fixture(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> RegenerationHold:
    """Holds every rebuild an edit of a channel asks for, until the scenario releases it."""
    hold = RegenerationHold()
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold


@pytest.fixture(name="export_hold")
def export_hold_fixture(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> ExportHold:
    """Holds every export at its first report, until the scenario releases it."""
    hold = ExportHold()
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold
