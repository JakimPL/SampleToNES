from pathlib import Path

from automation.screen import Screen


def gathered(screen: Screen, *paths: Path) -> None:
    """Waits until the list holds a row for each of ``paths`` and no other row."""
    converter = screen.main.converter
    expected = sorted(converter.list.row(path) for path in paths)
    screen.expect(
        lambda: sorted(converter.list.rows()),
        expected.__eq__,
        description=f"the list holding {[path.name for path in paths]} alone",
    )
