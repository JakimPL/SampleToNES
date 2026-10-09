import operator
from pathlib import Path
from typing import Dict, List

from automation.screen import Screen
from tests.screens.main.run.constants import RECONSTRUCTION_SUFFIX, RUN_TIMEOUT_SECONDS


def run_to_its_end(screen: Screen) -> None:
    """Presses the button naming the run and waits for the question its end asks, which it closes."""
    converter = screen.main.converter
    converter.press_action()
    wait_for_the_end(screen)


def wait_for_the_end(screen: Screen) -> None:
    """Waits for the question the run's end asks and closes it."""
    converter = screen.main.converter
    screen.bridge.expect(converter.end_prompt.is_shown, bool, description="the run's end", timeout=RUN_TIMEOUT_SECONDS)
    converter.end_prompt.cancel()
    screen.expect(converter.end_prompt.is_shown, operator.not_, description="the end closed")


def written(destination: Path) -> List[Path]:
    """The reconstruction files below ``destination``, sorted."""
    return sorted(destination.rglob(f"*{RECONSTRUCTION_SUFFIX}"))


def modified(paths: List[Path]) -> Dict[Path, int]:
    """The modification time of each of ``paths``, in nanoseconds."""
    return {path: path.stat().st_mtime_ns for path in paths}
