from typing import Final, List

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.skipped import SkippedRow
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.voices.note_on import NoteOn

MISSING_VOICE_ID: Final[str] = "a-voice-no-project-holds"
SILENT_ROW: Final[int] = 5
SILENT_CHANNEL: Final[ChannelName] = ChannelName.PULSE1


def name_a_missing_voice(project: Project) -> SkippedRow:
    """Puts a note-on on the first frame naming a voice that has no instrument on its channel.

    Returns:
        SkippedRow: The row an export reports for it.
    """
    rows: List[Row] = [Row() for _ in range(project.song.rows_per_pattern)]
    rows[SILENT_ROW] = Row(command=NoteOn(voice_id=MISSING_VOICE_ID))
    project.song.channels[SILENT_CHANNEL] = Channel(name=SILENT_CHANNEL, patterns={0: Pattern(rows=rows)})
    project.song.order[0][SILENT_CHANNEL] = 0
    return SkippedRow(
        voice_id=MISSING_VOICE_ID,
        channel=SILENT_CHANNEL,
        order_position=0,
        row_index=SILENT_ROW,
    )
