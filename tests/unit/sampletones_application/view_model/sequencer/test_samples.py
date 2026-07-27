import pytest

from sampletones_application.view_model.sequencer.samples import SampleSelection


class TestSampleSelectionLabel:
    @pytest.mark.parametrize(
        ("position", "name", "expected"),
        [
            (0, "Kick", "00: Kick"),
            (26, "Bass", "1A: Bass"),
            (255, "Lead", "FF: Lead"),
        ],
    )
    def test_label_pairs_the_hex_position_with_the_name(
        self,
        position: int,
        name: str,
        expected: str,
    ) -> None:
        selection = SampleSelection(sample_id="id", position=position, name=name)

        assert selection.label == expected
