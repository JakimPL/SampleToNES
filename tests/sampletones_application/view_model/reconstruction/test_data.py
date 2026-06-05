from typing import Callable

from sampletones_application.view_model.reconstruction.data import ReconstructionData
from sampletones_core.reconstructions import Reconstruction


class TestFromReconstruction:
    def test_wraps_the_same_object_for_live_linking(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        reconstruction = reconstruction_factory()

        data = ReconstructionData.from_reconstruction(reconstruction)

        assert data.reconstruction is reconstruction
        assert data.filepath == reconstruction.audio_filepath
