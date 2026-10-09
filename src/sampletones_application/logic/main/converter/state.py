from dataclasses import dataclass, replace
from typing import Optional, Self

from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.settings import RunSettings
from sampletones_application.logic.main.sources.key import SourceKey


@dataclass(frozen=True)
class ConverterState:
    """What the converter is set up to do, as one value every gesture rewrites a part of.

    The sides answer to each other — the settings say what a run hands out, the gathering says
    which recordings take part, and the destination follows from both — so a gesture states the one
    side it changes and hands the whole state back to be settled at once. ``selected`` names the
    row a reader is inspecting, which the settings card edits and the list draws as picked out.
    """

    settings: RunSettings
    gathering: Gathering
    destination: Destination
    selected: Optional[SourceKey]

    def with_settings(self, settings: RunSettings) -> Self:
        return replace(self, settings=settings)

    def with_gathering(self, gathering: Gathering) -> Self:
        return replace(self, gathering=gathering)

    def with_destination(self, destination: Destination) -> Self:
        return replace(self, destination=destination)

    def with_selected(self, selected: Optional[SourceKey]) -> Self:
        return replace(self, selected=selected)

    def selecting(self, selected: Optional[SourceKey]) -> Self:
        """The state with ``selected`` inspected, where the list still holds the row it names."""
        if selected is not None and self.gathering.sources.row(selected) is None:
            return replace(self, selected=None)

        return replace(self, selected=selected)
