from dataclasses import dataclass
from typing import Dict, Final, Optional, Self, Tuple

from sampletones_application.categories.elements.sequencer import (
    SequencerVoicesElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_core.formats.famitracker.voice import InstrumentOmission

OMISSION_ELEMENTS: Final[Dict[InstrumentOmission, SequencerVoicesElements]] = {
    InstrumentOmission.CUMULATIVE_BEND: SequencerVoicesElements.OMISSION_CUMULATIVE_BEND,
    InstrumentOmission.RELEASE_POINT: SequencerVoicesElements.OMISSION_RELEASE_POINT,
    InstrumentOmission.ARPEGGIO_MODE: SequencerVoicesElements.OMISSION_ARPEGGIO_MODE,
}

OMISSION_BULLET: Final[str] = "  - "


def omission_label(
    language_manager: LanguageManager,
    element: SequencerVoicesElements,
) -> str:
    """Resolves the words one dimension of a tracker instrument is named in."""
    return language_manager[
        Page.SEQUENCER,
        Panel.VOICES,
        TextType.LABEL,
        element,
    ]


@dataclass(frozen=True)
class InstrumentImportMessages:
    """The words a read instrument file is reported in.

    A ``.fti`` states a channel's whole instrument, and a voice takes every envelope it holds.
    Whatever the file states past them stays in the file, so the import names it in the reader's
    own words as the voice arrives.

    Attributes:
        title: Title of the dialog reporting a finished import.
        template: The opening lines, naming the voice that arrived.
        omissions: The words each dimension a file states past the voice is named in.
    """

    title: str
    template: str
    omissions: Dict[InstrumentOmission, str]

    @classmethod
    def build(cls, language_manager: LanguageManager) -> Self:
        """Resolves every word the import report prints.

        Args:
            language_manager: The catalog the words are read from.

        Returns:
            Self: The bundle the import handler reads.
        """
        return cls(
            title=language_manager["sequencer.voices.title.instrument_imported"],
            template=language_manager["sequencer.voices.template.instrument_omissions"],
            omissions={
                omission: omission_label(
                    language_manager,
                    element,
                )
                for omission, element in OMISSION_ELEMENTS.items()
            },
        )

    def notice(
        self,
        name: str,
        omissions: Tuple[InstrumentOmission, ...],
    ) -> Optional[str]:
        """Phrases what an instrument file held beyond the voice it made.

        The dimensions are named in the order the reader states them, so one wording describes a
        file however many of them it carries.

        Args:
            name: The name the voice arrived under.
            omissions: What the instrument file stated past the voice's envelopes.

        Returns:
            Optional[str]: The report the import dialog prints, or ``None`` where the file
            stated the voice alone.
        """
        if not omissions:
            return None

        return "\n".join(
            (
                self.template.format(name=name),
                self._listed(omissions),
            ),
        )

    def _listed(self, omissions: Tuple[InstrumentOmission, ...]) -> str:
        """The dimensions a file states past the voice, one to a line under its own mark."""
        return "\n".join(f"{OMISSION_BULLET}{self.omissions[omission]}" for omission in omissions)
