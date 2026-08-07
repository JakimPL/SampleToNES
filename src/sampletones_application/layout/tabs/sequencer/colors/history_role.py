from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class HistoryRoleColors(BaseModel, extra="forbid", frozen=True):
    """Colours for the history-detail token roles unique to the detail line.

    The instrument/transpose/volume, frame, row, and sample tokens draw from the
    shared :class:`TrackerColors` palette; only the roles unique to the detail line
    live here.
    """

    channel: WrittenColor
    value: WrittenColor
    separator: WrittenColor
