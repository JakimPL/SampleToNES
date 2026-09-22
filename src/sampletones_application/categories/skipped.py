from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, Optional, Self, Tuple

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.skipped import SkippedRow
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.structures import IdentifiedCollection
from sampletones_core.utils.display import display_id, display_voice_label

MAX_REPORTED_ROWS: Final[int] = 12
ROW_BULLET: Final[str] = "  - "


@dataclass(frozen=True)
class SkippedRowMessages:
    """The words the rows an export left silent are reported in.

    A row naming a voice on a channel the voice has no instrument for plays nothing in the song,
    so the tracker formats write a note cut there. The report names each row where the reader
    finds it in the tracker, and closes on how many more the list leaves out.

    Attributes:
        heading: The line introducing the rows.
        row: The template one row is printed with.
        more: The template naming the rows past the ones listed.
        channels: The name each channel is printed under.
    """

    heading: str
    row: str
    more: str
    channels: Dict[ChannelName, str]

    @classmethod
    def build(cls, language_manager: LanguageManager) -> Self:
        """Resolves every word the report prints.

        Args:
            language_manager: The catalog the words are read from.

        Returns:
            Self: The bundle the export result handler reads.
        """
        return cls(
            heading=language_manager["global.dialog.message.export_skipped_rows"],
            row=language_manager["global.dialog.template.export_skipped_row"],
            more=language_manager["global.dialog.template.export_skipped_rows_more"],
            channels={channel: channel_label(language_manager, channel) for channel in ChannelName.items()},
        )

    def notice(
        self,
        skipped_rows: Tuple[SkippedRow, ...],
        voices: IdentifiedCollection[VoiceUnion],
    ) -> Optional[str]:
        """Phrases the rows an export wrote as a note cut.

        Args:
            skipped_rows: The rows the export left silent, in the order the song plays them.
            voices: The project's voices, which the rows name their voice through.

        Returns:
            Optional[str]: The lines the export dialog appends, and ``None`` where no row was
            left silent.
        """
        if not skipped_rows:
            return None

        listed = skipped_rows[:MAX_REPORTED_ROWS]
        lines = [self.heading, *(f"{ROW_BULLET}{self._row(skipped, voices)}" for skipped in listed)]
        remaining = len(skipped_rows) - len(listed)
        if remaining > 0:
            lines.append(self.more.format(count=remaining))

        return "\n".join(lines)

    def _row(
        self,
        skipped: SkippedRow,
        voices: IdentifiedCollection[VoiceUnion],
    ) -> str:
        return self.row.format(
            frame=display_id(skipped.order_position),
            channel=self.channels[skipped.channel],
            row=display_id(skipped.row_index),
            voice=self._voice(skipped.voice_id, voices),
        )

    @staticmethod
    def _voice(voice_id: str, voices: IdentifiedCollection[VoiceUnion]) -> str:
        """The voice as the voices list prints it, and blank where the project no longer holds it."""
        voice = voices.get(voice_id)
        if voice is None:
            return display_id(None)

        return display_voice_label(voices.get_index(voice_id), voice.name)
