from pathlib import Path
from typing import Dict, Final, Tuple

VERSION: Final[str] = "1.0"
OTHER_VERSION: Final[str] = "1.1"
CONVERTING_PACKAGE: Final[str] = "converting"
JUDGING_PACKAGE: Final[str] = "judging"
MODULE: Final[str] = "conversion.py"
REFEREE_MODULE: Final[str] = "referee.py"
EDITED_MODULE: Final[str] = "SCALE = 2\n"
CONFIGURATION: Final[str] = "configs/defaults.yaml"
SOURCE_FILES: Final[Dict[str, Dict[str, str]]] = {
    CONVERTING_PACKAGE: {
        "__init__.py": "",
        MODULE: "SCALE = 1\n",
        CONFIGURATION: "scale: 1\n",
    },
    JUDGING_PACKAGE: {
        "__init__.py": "",
        REFEREE_MODULE: "TOLERANCE = 3\n",
        "settings.yaml": "tolerance: 3\n",
    },
}


def write_source(root: Path) -> Tuple[Path, ...]:
    """A source tree of two packages, each a few modules and a configuration file, as their directories."""
    for package, files in SOURCE_FILES.items():
        for name, content in files.items():
            path = root / package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    return tuple(root / package for package in SOURCE_FILES)


def edit_source(packages: Tuple[Path, ...]) -> None:
    """Edit one module of the tree, as a developer does between two runs."""
    (packages[0] / MODULE).write_text(EDITED_MODULE, encoding="utf-8")
