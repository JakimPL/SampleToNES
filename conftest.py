import importlib.util
from pathlib import Path
from typing import Final, Optional, Tuple

JEEPNEY_MODULE: Final[str] = "jeepney"

PORTAL_PATHS: Final[Tuple[str, ...]] = (
    "src/sampletones_application/utils/file_dialogs/backends/portal",
    "tests/unit/sampletones_application/utils/file_dialogs/backends/portal",
    "tests/unit/sampletones_application/utils/file_dialogs/test_selection.py",
)

PORTAL_LIBRARY_INSTALLED: Final[bool] = importlib.util.find_spec(JEEPNEY_MODULE) is not None


def pytest_ignore_collect(collection_path: Path) -> Optional[bool]:
    """
    Keeps collection to the modules the running platform imports.

    ``jeepney`` is declared for Linux alone, so what speaks to the desktop portal is collected
    where that library is installed. The behaviour those modules describe belongs to the Linux
    desktop, and the Linux runs of the suite cover it.

    Args:
        collection_path: The file or directory pytest is about to look into.

    Returns:
        Optional[bool]: ``True`` for a path that stays out of collection, ``None`` to leave the
            choice with pytest.
    """
    if PORTAL_LIBRARY_INSTALLED:
        return None

    root = Path(__file__).parent
    if any(collection_path.is_relative_to(root / path) for path in PORTAL_PATHS):
        return True

    return None
