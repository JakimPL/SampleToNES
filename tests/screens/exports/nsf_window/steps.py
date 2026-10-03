from pathlib import Path


def folder(name: str) -> Path:
    """Creates and returns a folder of the home for the program, as a native dialog's answer would name it."""
    path = Path.cwd() / "exports" / name
    path.mkdir(parents=True, exist_ok=True)
    return path
