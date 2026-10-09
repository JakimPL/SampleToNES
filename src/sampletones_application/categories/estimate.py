from typing import Optional

from sampletones_application.categories.manager import LanguageManager
from sampletones_shared.utils.time import format_span


def time_estimation(
    language_manager: LanguageManager,
    eta_seconds: Optional[float],
) -> str:
    """How long a run has left, phrased to sit beside the count it is reported with.

    A run needs two measurements before it has a rate, so the first moments of one read the mark
    the language file keeps for an estimate still being taken, and every later moment reads the
    span itself. Both keys are read here, at the moment the line is composed, so a language
    chosen mid-run reaches the next reading.

    Args:
        language_manager: Where the template and the mark are read from.
        eta_seconds: The seconds the run has left, or ``None`` while its rate is still being taken.

    Returns:
        str: The clause a status line carries, as ``" (ETA: 2m 13s)"``.
    """
    span = language_manager["global.dialog.label.unknown_duration"] if eta_seconds is None else format_span(eta_seconds)
    return language_manager["global.dialog.template.time_estimation"].format(eta_string=span)
