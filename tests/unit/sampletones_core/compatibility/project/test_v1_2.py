from typing import Any, Dict

from sampletones_core.compatibility.fields import KIND, KIND_SAMPLE, SAMPLES, VOICES
from sampletones_core.compatibility.project.v1_2 import update


def _pool_with_row(command: Dict[str, Any]) -> Dict[str, Any]:
    return {"name": "pulse1", "patterns": {"0": {"rows": [{"command": command}]}}}


def _first_command(data: Dict[str, Any]) -> Dict[str, Any]:
    command: Dict[str, Any] = data["song"]["channels"]["pulse1"]["patterns"]["0"]["rows"][0]["command"]
    return command


class TestProjectV1_2:
    def test_gathers_samples_into_voices(self) -> None:
        data = {SAMPLES: [{"id": "a", "name": "Lead", "reconstruction_id": "r"}]}

        upgraded = update(data)

        assert SAMPLES not in upgraded
        assert upgraded[VOICES] == [{KIND: KIND_SAMPLE, "id": "a", "name": "Lead", "reconstruction_id": "r"}]

    def test_names_the_voice_alone(self) -> None:
        data = {"song": {"channels": {"pulse1": _pool_with_row({"sample_id": "a", "channel_name": "pulse1"})}}}

        upgraded = update(data)

        assert _first_command(upgraded) == {"voice_id": "a"}

    def test_leaves_note_off_commands_untouched(self) -> None:
        data = {"song": {"channels": {"pulse1": _pool_with_row({})}}}

        assert _first_command(update(data)) == {}

    def test_leaves_the_input_untouched(self) -> None:
        data = {SAMPLES: [{"id": "a", "name": "Lead", "reconstruction_id": "r"}]}

        update(data)

        assert SAMPLES in data

    def test_document_without_samples_or_a_song_stays_the_same_shape(self) -> None:
        data = {"format_version": "1.1"}

        assert update(data) == data
