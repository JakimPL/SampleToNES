from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sampletones_application.utils.file_dialogs.filter import FileFilter


@dataclass(frozen=True)
class SaveDestination:
    """
    Where a save dialog was told to write, and the file type it was chosen under.

    A dialog whose type selector reports the active type carries it in ``file_type``, one of the
    types the dialog was asked to offer, which is what lets the API layer settle the extension
    from the type the user picked. A dialog that answers with a name alone leaves it ``None``,
    and the extension then follows from the name and the type the dialog opened on.
    """

    path: Path
    file_type: Optional[FileFilter]


def untyped_destination(path: Optional[Path]) -> Optional[SaveDestination]:
    """
    Returns the destination a dialog answering with a name alone gives, for the name it answered.

    Args:
        path: The name the dialog answered with, or ``None`` once it was dismissed.

    Returns:
        Optional[SaveDestination]: The destination carrying that name, or ``None`` for a
        dismissed dialog.
    """
    if path is None:
        return None

    return SaveDestination(path=path, file_type=None)
