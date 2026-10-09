import operator
from pathlib import Path

from automation.screen import Screen


def folder(name: str) -> Path:
    """Creates and returns a folder of the home for one door's files, as a native dialog's answer would name it."""
    path = Path.cwd() / "exports" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def written_project(screen: Screen, exported_key: str, destination: Path) -> str:
    """Waits for the notice of the project export ``exported_key`` words, dismisses it, and returns what it said."""
    notice = screen.exports.project_notice
    screen.expect(notice.is_shown, bool, description=f"{destination.name} written")
    words = notice.words()
    assert screen.words(exported_key) in words
    assert destination.is_file()
    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the notice gone")
    return words
