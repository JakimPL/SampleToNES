from pathlib import Path

from sampletones_shared.logger import logger
from sampletones_shared.utils.system.opening import select_file_opener


def open_page(page: Path) -> bool:
    """
    Show the page in the reader's own browser.

    A run ends with what it wrote in front of the person who started it, on whichever system they
    are on, and a system with no browser to reach leaves them the link the run printed.

    Args:
        page: The page to open.

    Returns:
        bool: Whether a browser took the page.
    """
    try:
        select_file_opener().open(page.resolve())
    except OSError:
        logger.info("No browser answered; open the page from the link above")
        return False

    return True
