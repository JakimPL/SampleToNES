from unittest.mock import Mock

from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.sample import Sample


class TestSampleClone:
    def test_clone_gets_a_fresh_id(self) -> None:
        sample = Sample(name="lead", reconstruction=Mock())
        assert sample.clone().id != sample.id

    def test_clone_carries_name_and_loop(self) -> None:
        sample = Sample(name="lead", reconstruction=Mock(), loop_point=WHOLE_LOOP_POINT)
        clone = sample.clone()
        assert clone.name == "lead"
        assert clone.loop_point == WHOLE_LOOP_POINT

    def test_clone_deep_copies_the_reconstruction(self) -> None:
        reconstruction = Mock()
        sample = Sample(name="lead", reconstruction=reconstruction)
        clone = sample.clone()
        reconstruction.model_copy.assert_called_once_with(deep=True)
        assert clone.reconstruction is reconstruction.model_copy.return_value
