from dataclasses import dataclass
from typing import Optional, Self

from sampletones_application.categories.manager import LanguageManager
from sampletones_core.exporters.truncation import EnvelopeTruncation


@dataclass(frozen=True)
class TruncationMessages:
    """The words one kind of export reports its shortened envelopes in.

    A tracker stores a bounded number of values per dimension, so an export shortens a longer one
    and says so beside the files it wrote. Each kind of export names the shortening its own way:
    one instrument by the frames it kept of the frames it had, several by how many were shortened.

    Attributes:
        template: The line naming the frames kept, the frames given and the instruments shortened.
    """

    template: str

    @classmethod
    def for_instrument(cls, language_manager: LanguageManager) -> Self:
        """The words an export of one instrument reports its shortening in.

        Args:
            language_manager: The catalog the words are read from.

        Returns:
            Self: The bundle the export result handler reads.
        """
        return cls(template=language_manager["reconstructions.instruments.message.export_instrument_truncated"])

    @classmethod
    def for_instruments(cls, language_manager: LanguageManager) -> Self:
        """The words an export of a reconstruction's instruments reports its shortening in.

        Args:
            language_manager: The catalog the words are read from.

        Returns:
            Self: The bundle the export result handler reads.
        """
        return cls(template=language_manager["reconstructions.instruments.message.export_instruments_truncated"])

    @classmethod
    def for_project(cls, language_manager: LanguageManager) -> Self:
        """The words an export of a whole song reports its shortening in.

        Args:
            language_manager: The catalog the words are read from.

        Returns:
            Self: The bundle the export result handler reads.
        """
        return cls(template=language_manager["global.dialog.template.export_truncated"])

    def notice(self, truncation: Optional[EnvelopeTruncation]) -> Optional[str]:
        """Phrases what an export left out of the envelopes it wrote.

        Args:
            truncation: The shortening the export underwent, or ``None`` where it fit whole.

        Returns:
            Optional[str]: The line the export dialog appends, and ``None`` where every envelope
            was written whole.
        """
        if truncation is None:
            return None

        return self.template.format(
            frames=truncation.frames,
            source_frames=truncation.source_frames,
            instruments=truncation.instruments,
        )
