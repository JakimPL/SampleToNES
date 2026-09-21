from typing import Optional

from pydantic import BaseModel

from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.enums import HierarchyMode


class ReconstructionStemsViewModel(BaseModel, frozen=True):
    """What the stems card renders for the loaded reconstruction.

    The recorded assignment is a stems list like the converter's, so the card hands
    :attr:`stems` straight to the shared element and keeps the setup line describing how the
    levels were picked.
    """

    reconstruction_loaded: bool
    stems: StemsListViewModel
    hierarchy_mode: Optional[HierarchyMode] = None

    @property
    def show_setup_line(self) -> bool:
        """The setup line states how the levels of a stems record took turns."""
        return self.hierarchy_mode is not None

    @property
    def show_empty_state(self) -> bool:
        """The empty state explains a loaded reconstruction that records no source."""
        return self.reconstruction_loaded and not self.stems.rows
