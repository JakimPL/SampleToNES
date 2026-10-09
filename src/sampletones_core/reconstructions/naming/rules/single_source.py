from pathlib import Path
from typing import Tuple


class SingleSourceRule:
    """Names a reconstruction after its one source recording."""

    def applies(self, source_paths: Tuple[Path, ...]) -> bool:
        return len(source_paths) == 1

    def derive(self, source_paths: Tuple[Path, ...]) -> str:
        return source_paths[0].stem
