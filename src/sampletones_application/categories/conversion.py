from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Self, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.skipped import ROW_BULLET

MAX_REPORTED_RECORDINGS: Final[int] = 8
ONE_RECORDING: Final[int] = 1


@dataclass(frozen=True)
class SkippedRecordingMessages:
    """The words a batch reports the recordings it went on without in.

    A batch converts each recording on its own, so a recording that fails is skipped and the rest are
    converted. The report counts the skipped recordings, names each by its file name, and closes on how
    many more it leaves out. The log keeps the error each one ended in.

    Attributes:
        one: The heading over a single skipped recording.
        several: The heading counting several skipped recordings.
        more: The line naming the recordings past the ones listed.
    """

    one: str
    several: str
    more: str

    @classmethod
    def build(cls, language_manager: LanguageManager) -> Self:
        """Resolves every word the report prints.

        Args:
            language_manager: The catalog the words are read from.

        Returns:
            Self: The bundle the end of a conversion reads.
        """
        return cls(
            one=language_manager["main.converter.message.skipped_recording_heading"],
            several=language_manager["main.converter.template.skipped_recordings_heading"],
            more=language_manager["main.converter.template.skipped_recordings_more"],
        )

    def notice(self, skipped: Tuple[Path, ...]) -> Optional[str]:
        """Phrases the recordings a batch skipped, under a heading that counts them.

        Args:
            skipped: The recordings the batch went on without, in the order it reached them.

        Returns:
            Optional[str]: The paragraph the end of a conversion appends, and ``None`` where every
            recording was converted.
        """
        if not skipped:
            return None

        listed = skipped[:MAX_REPORTED_RECORDINGS]
        heading = self.one if len(skipped) == ONE_RECORDING else self.several.format(count=len(skipped))
        lines = [heading, *(f"{ROW_BULLET}{recording.name}" for recording in listed)]
        remaining = len(skipped) - len(listed)
        if remaining > 0:
            lines.append(self.more.format(count=remaining))

        return "\n".join(lines)
