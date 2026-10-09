import pytest

from sampletones_application.view_model.sequencer.voices import VoiceKind, VoiceSelection


class TestVoiceSelectionLabel:
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
        selection = VoiceSelection(voice_id="id", position=position, name=name, kind=VoiceKind.SAMPLE)

        assert selection.label == expected
