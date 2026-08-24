from typing import Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.editing import (
    EditedVoice,
    InstrumentEdit,
    ReconstructionEdit,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.instrument import Instrument


class InstrumentEditor:
    """Which voice the Reconstructions tab has in front of it, and where an edit to it goes.

    The tab shows one voice at a time: a reconstruction, whose waveform and stems the rest of the
    tab draws, or an instrument, which has none of those and is its envelopes alone. Opening one puts
    the other away, so the cards beside the instruments panel always describe what it is editing.
    """

    def __init__(
        self,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
    ) -> None:
        self._reconstruction_manager = reconstruction_manager
        self._controller = project_controller
        self._voice_id: Optional[str] = None

    def edit_instrument(self, voice_id: str) -> None:
        """Puts an instrument in front of the tab, closing whatever reconstruction it held."""
        self._voice_id = voice_id
        self._reconstruction_manager.close_reconstruction()

    def release_instrument(self) -> None:
        """Lets go of the instrument, which is what opening a reconstruction does."""
        self._voice_id = None

    @property
    def instrument(self) -> Optional[Instrument]:
        """The instrument in front of the tab, or ``None`` where it holds a reconstruction or nothing."""
        if self._voice_id is None:
            return None

        voice = self._controller.project.voices.get(self._voice_id)
        return voice if isinstance(voice, Instrument) else None

    def edited_instrument(self) -> Optional[EditedVoice]:
        """What the instruments panel is editing, or ``None`` while it holds nothing."""
        instrument = self.instrument
        if instrument is not None:
            return InstrumentEdit(
                voice_id=instrument.id,
                name=instrument.name,
                features=instrument.instrument_features(),
            )

        feature_data = self._reconstruction_manager.current_features
        return None if feature_data is None else ReconstructionEdit(channels=feature_data.channels)

    def write_envelope(self, feature_key: FeatureKey, envelope: Envelope[int]) -> None:
        """Writes one dimension of the instrument in front of the tab.

        Raises:
            TypeError: If the tab holds no instrument to write into.
        """
        instrument = self.instrument
        if instrument is None:
            raise TypeError("The tab holds no instrument to write an envelope into")

        self._controller.set_instrument_envelope(instrument.id, feature_key, envelope)
