from typing import Optional, Tuple

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.editing import (
    EditedInstrument,
    ReconstructionEdit,
    ShapeEdit,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_core.constants.enums import FeatureKey
from sampletones_core.project.voices.shape import Shape
from sampletones_core.types.feature import FeatureValue


class InstrumentEditor:
    """Which voice the Reconstructions tab has in front of it, and where an edit to it goes.

    The tab shows one voice at a time: a reconstruction, whose waveform and stems the rest of the
    tab draws, or a shape, which has none of those and is its envelopes alone. Opening one puts
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

    def edit_shape(self, voice_id: str) -> None:
        """Puts a shape in front of the tab, closing whatever reconstruction it held."""
        self._voice_id = voice_id
        self._reconstruction_manager.close_reconstruction()

    def release_shape(self) -> None:
        """Lets go of the shape, which is what opening a reconstruction does."""
        self._voice_id = None

    @property
    def shape(self) -> Optional[Shape]:
        """The shape in front of the tab, or ``None`` where it holds a reconstruction or nothing."""
        if self._voice_id is None:
            return None

        voice = self._controller.project.voices.get(self._voice_id)
        return voice if isinstance(voice, Shape) else None

    def edited_instrument(self) -> Optional[EditedInstrument]:
        """What the instruments panel is editing, or ``None`` while it holds nothing."""
        shape = self.shape
        if shape is not None:
            return ShapeEdit(
                voice_id=shape.id,
                name=shape.name,
                features=shape.instrument_features(),
                root_pitch=shape.root_pitch,
                root_period=shape.root_period,
                loop_point=shape.loop_point,
            )

        feature_data = self._reconstruction_manager.current_features
        return None if feature_data is None else ReconstructionEdit(channels=feature_data.channels)

    def write_envelope(self, feature_key: FeatureKey, data: FeatureValue) -> None:
        """Writes one dimension of the shape in front of the tab.

        Raises:
            TypeError: If the tab holds no shape to write into.
        """
        shape = self.shape
        if shape is None:
            raise TypeError("The tab holds no shape to write an envelope into")

        self._controller.set_shape_envelope(shape.id, feature_key, _items(data))

    def write_roots(self, *, pitch: int, period: int) -> None:
        """Moves the roots the shape in front of the tab is measured against.

        Raises:
            TypeError: If the tab holds no shape to write into.
        """
        shape = self.shape
        if shape is None:
            raise TypeError("The tab holds no shape to move the roots of")

        self._controller.set_shape_root(shape.id, pitch=pitch, period=period)

    def write_loop_point(self, loop_point: Optional[int]) -> None:
        """Sets the tick the shape in front of the tab repeats from.

        Raises:
            TypeError: If the tab holds no shape to write into.
        """
        shape = self.shape
        if shape is None:
            raise TypeError("The tab holds no shape to set a loop point on")

        self._controller.set_voice_loop_point(shape.id, loop_point)


def _items(data: FeatureValue) -> Tuple[int, ...]:
    """The items an envelope edit carries, as the plain tuple a shape stores."""
    if isinstance(data, int):
        return (data,)

    return tuple(int(value) for value in data)
