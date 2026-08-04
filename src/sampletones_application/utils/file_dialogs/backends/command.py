import subprocess
from pathlib import Path
from typing import List, Optional

from sampletones_shared.utils.system.paths import normalize_path


def run_dialog_command(command: List[str]) -> Optional[Path]:
    """
    Runs a command-line dialog tool and returns the path it reports.

    ``kdialog`` and ``zenity`` share one contract: the chosen path arrives on standard output,
    and a dismissed dialog leaves that output empty, which answers ``None``. The exit status
    carries the same dismissal, so the reported path alone decides the answer.

    Args:
        command (List[str]): The tool and the arguments to run it with.

    Returns:
        Optional[Path]: The path the dialog reports, or ``None`` once the dialog is dismissed.
    """
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return normalize_path(result.stdout.strip())
