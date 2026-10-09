from typing import Final

from .model import BoardPage

DATA_GLOBAL: Final[str] = "BOARD"


def data_script(page: BoardPage) -> str:
    """The page's own contents, as the one global its script reads.

    Everything the page draws travels as data — the sounds, the scores, the clips and the channel
    colors — so the script it is read by holds layout alone and stays the same from run to run.

    Args:
        page: Everything the page draws.

    Returns:
        The script assigning the page's contents to its global.
    """
    return f"const {DATA_GLOBAL} = {page.model_dump_json(indent=1)};\n"
