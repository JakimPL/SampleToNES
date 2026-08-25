from pathlib import Path
from typing import Tuple


class CommonDirectoryRule:
    """Names a reconstruction after the directory all of its sources share."""

    def applies(self, source_paths: Tuple[Path, ...]) -> bool:
        return len(source_paths) > 1 and len({path.parent for path in source_paths}) == 1

    def derive(self, source_paths: Tuple[Path, ...]) -> str:
        return source_paths[0].parent.name
