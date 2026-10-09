from pathlib import Path
from typing import Final, Optional, Tuple

from sampletones_shared.utils.system.modules import JEEPNEY_MODULE, module_available

JEEPNEY_PATHS: Final[Tuple[str, ...]] = (
    "src/sampletones_application/utils/file_dialogs/backends/portal",
    "src/sampletones_shared/utils/system/reveal/file_manager1.py",
    "tests/unit/sampletones_application/utils/file_dialogs/backends/portal",
    "tests/unit/sampletones_application/utils/file_dialogs/test_selection.py",
    "tests/unit/sampletones_shared/utils/system/reveal/test_file_manager1.py",
)

JEEPNEY_INSTALLED: Final[bool] = module_available(JEEPNEY_MODULE)


def pytest_ignore_collect(collection_path: Path) -> Optional[bool]:
    """
    Keeps collection to the modules the running platform imports.

    ``jeepney`` is declared for Linux alone, so what speaks D-Bus — the desktop portal's file
    dialogs and the ``FileManager1`` reveal backend — is collected where that library is
    installed. The behavior those modules describe belongs to the Linux desktop, and the Linux
    runs of the suite cover it.

    Args:
        collection_path: The file or directory pytest is about to look into.

    Returns:
        Optional[bool]: ``True`` for a path that stays out of collection, ``None`` to leave the
            choice with pytest.
    """
    if JEEPNEY_INSTALLED:
        return None

    root = Path(__file__).parent
    if any(collection_path.is_relative_to(root / path) for path in JEEPNEY_PATHS):
        return True

    return None
