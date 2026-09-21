from dataclasses import dataclass, replace
from typing import Self

from sampletones_application.constants.output import OutputKind
from sampletones_core.constants.enums import HierarchyMode
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


@dataclass(frozen=True)
class RunSettings:
    """The choices a run holds to, whatever it converts.

    ``joining`` is what a recording is given when it joins the setup, and each recording carries
    its own settings from there, so what a run reaches is what its rows hold. The rest name the
    shape of the run itself — what it writes, and how the levels take turns.
    """

    joining: StemSettings
    output: OutputKind
    hierarchy_mode: HierarchyMode

    @property
    def mixes(self) -> bool:
        """Several recordings are being gathered into one reconstruction."""
        return self.output.mixes

    def with_joining(self, joining: StemSettings) -> Self:
        """The settings every recording gathered from here on starts with."""
        return replace(self, joining=joining)

    def with_output(self, output: OutputKind) -> Self:
        """The run writing one reconstruction per gathered recording, or one from them all."""
        return replace(self, output=output)

    def with_hierarchy_mode(self, hierarchy_mode: HierarchyMode) -> Self:
        """The run taking its levels round by round, or one level exhausted before the next."""
        return replace(self, hierarchy_mode=hierarchy_mode)
