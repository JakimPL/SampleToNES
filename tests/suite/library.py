from pathlib import Path


class WrittenLibrary:
    """Library data standing in for a generated library, written as the file the catalog lists."""

    def save(self, path: Path) -> None:
        path.touch()
