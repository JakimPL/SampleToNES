from typing import Callable

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_core.reconstructions import Reconstruction


class TestFromReconstruction:
    def test_wraps_the_same_object_for_live_linking(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()

        data = ReconstructionData.from_reconstruction(reconstruction)

        assert data.reconstruction is reconstruction

    def test_has_no_filepath_for_in_memory_reconstruction(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()

        data = ReconstructionData.from_reconstruction(reconstruction)
        assert data.filepath is None
