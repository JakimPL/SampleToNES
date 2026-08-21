import os
from pathlib import Path
from typing import Tuple


class CommonPrefixRule:
    """Names a reconstruction after the filename prefix every source shares."""

    def applies(self, source_paths: Tuple[Path, ...]) -> bool:
        if len(source_paths) < 2:
            return False

        return bool(self._common_prefix(source_paths))

    def derive(self, source_paths: Tuple[Path, ...]) -> str:
        return self._common_prefix(source_paths)

    @staticmethod
    def _common_prefix(source_paths: Tuple[Path, ...]) -> str:
        stems = [path.stem for path in source_paths]
        return os.path.commonprefix(stems).rstrip("_- ")
