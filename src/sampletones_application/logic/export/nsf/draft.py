from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from sampletones_application.logic.export.nsf.source.protocol import NSFExportSource
from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_player.builder import SONG_START
from sampletones_player.export.program import NSFProgram


@dataclass(frozen=True)
class NSFExportDraft:
    """An NSF export as it stands while its dialog is open.

    Attributes:
        source: What the export writes.
        offer: What the source leaves to choose, read once the dialog opens.
        choices: The choices the dialog stands at.
        destination: The file the export writes.
    """

    source: NSFExportSource
    offer: NSFExportOffer
    choices: NSFExportChoices
    destination: Path

    def with_choices(self, choices: NSFExportChoices) -> NSFExportDraft:
        return replace(self, choices=choices)

    def with_destination(self, destination: Path) -> NSFExportDraft:
        return replace(self, destination=destination)

    def program(self) -> NSFProgram:
        """The program the standing choices write, its repeat placed on the source's own ticks.

        Raises:
            ValidationError: If no channel is ticked.
        """
        return NSFProgram(
            information=self.choices.information,
            channels=self.choices.channels,
            loop_tick=self._loop_tick(),
            scheme=self.choices.scheme,
        )

    def _loop_tick(self) -> Optional[int]:
        """The tick the song returns to: the first one, the one the chosen frame starts on, or none."""
        match self.choices.repeat:
            case NSFRepeat.ONCE:
                return None
            case NSFRepeat.FROM_START:
                return SONG_START
            case NSFRepeat.FROM_FRAME:
                return self.source.frame_tick(self.choices.loop_frame)

    def view(self) -> NSFExportViewModel:
        return NSFExportViewModel(
            offer=self.offer,
            choices=self.choices,
            destination=self.destination,
            ticks=self.source.ticks(self.choices.channels),
            nes_frequency=self.source.nes_frequency,
        )
