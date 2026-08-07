from pydantic import BaseModel

from sampletones_application.layout.tabs.sequencer.colors.history_role import HistoryRoleColors
from sampletones_application.utils.palette.colors.written import WrittenColor


class HistoryColors(BaseModel, extra="forbid", frozen=True):
    """Colours for the history detail: the dimmed tint of future (redoable) entries
    and the per-role token palette.
    """

    future: WrittenColor
    roles: HistoryRoleColors
