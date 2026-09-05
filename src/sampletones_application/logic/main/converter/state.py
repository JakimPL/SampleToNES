from dataclasses import dataclass, replace
from typing import Self

from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.settings import RunSettings


@dataclass(frozen=True)
class ConverterState:
    """What the converter is set up to do, as one value every gesture rewrites a part of.

    The three sides answer to each other — the settings say what a run hands out, the gathering
    says which recordings take part, and the destination follows from both — so a gesture states
    the one side it changes and hands the whole state back to be settled at once.
    """

    settings: RunSettings
    gathering: Gathering
    destination: Destination

    def with_settings(self, settings: RunSettings) -> Self:
        return replace(self, settings=settings)

    def with_gathering(self, gathering: Gathering) -> Self:
        return replace(self, gathering=gathering)

    def with_destination(self, destination: Destination) -> Self:
        return replace(self, destination=destination)
