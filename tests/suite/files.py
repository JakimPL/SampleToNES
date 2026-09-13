from pathlib import Path


def empty_file(directory: Path, name: str) -> Path:
    """Writes an empty file called ``name`` under ``directory``, which a check that reads only names and presence accepts."""
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path
