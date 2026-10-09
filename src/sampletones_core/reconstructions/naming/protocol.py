from pathlib import Path
from typing import Protocol, Tuple


class NameRule(Protocol):
    """One step of the naming hierarchy: it states which source sets it names and the name it derives."""

    def applies(self, source_paths: Tuple[Path, ...]) -> bool: ...

    def derive(self, source_paths: Tuple[Path, ...]) -> str: ...
