from unittest.mock import Mock

from sampletones_core.project.voices.sample import Sample


class TestSampleClone:
    def test_clone_gets_a_fresh_id(self) -> None:
        sample = Sample(name="lead", reconstruction=Mock())
        assert sample.clone().id != sample.id

    def test_clone_carries_the_name(self) -> None:
        sample = Sample(name="lead", reconstruction=Mock())

        assert sample.clone().name == "lead"

    def test_clone_shares_the_reconstruction(self) -> None:
        reconstruction = Mock()
        sample = Sample(name="lead", reconstruction=reconstruction)
        clone = sample.clone()
        assert clone.reconstruction is reconstruction
        assert clone.id != sample.id
