from typing import Any, Dict

from sampletones_core.compatibility.fields import (
    KIND,
    KIND_SAMPLE,
    NAME,
    SAMPLES,
    VOICE_ID,
    VOICES,
)
from sampletones_core.compatibility.project.v1_1 import update


def _pool(extra: Dict[str, Any]) -> Dict[str, Any]:
    return {"generator": "pulse1", "patterns": {}, **extra}


def _pool_with_row(command: Dict[str, Any]) -> Dict[str, Any]:
    return {"generator": "pulse1", "patterns": {"0": {"rows": [{"command": command}]}}}


def _song(command: Dict[str, Any]) -> Dict[str, Any]:
    return {"song": {"channels": {"pulse1": _pool_with_row(command)}}}


def _first_command(data: Dict[str, Any]) -> Dict[str, Any]:
    command: Dict[str, Any] = data["song"]["channels"]["pulse1"]["patterns"]["0"]["rows"][0]["command"]
    return command


class TestProjectV1_1:
    def test_gathers_samples_into_voices(self) -> None:
        data = {SAMPLES: [{"id": "a", "name": "Lead", "reconstruction_id": "r"}]}

        upgraded = update(data)

        assert SAMPLES not in upgraded
        assert upgraded[VOICES] == [{KIND: KIND_SAMPLE, "id": "a", "name": "Lead", "reconstruction_id": "r"}]

    def test_renames_channel_pool_field(self) -> None:
        data = {"song": {"channels": {"pulse1": _pool({})}}}

        upgraded = update(data)

        assert upgraded["song"]["channels"]["pulse1"][NAME] == "pulse1"
        assert "generator" not in upgraded["song"]["channels"]["pulse1"]

    def test_names_the_voice_alone(self) -> None:
        data = _song({"sample_id": "a", "generator_name": "pulse1"})

        upgraded = update(data)

        assert _first_command(upgraded) == {VOICE_ID: "a"}

    def test_leaves_note_off_commands_untouched(self) -> None:
        data = _song({})

        assert _first_command(update(data)) == {}

    def test_leaves_the_input_untouched(self) -> None:
        data = {SAMPLES: [{"id": "a", "name": "Lead"}], **_song({"sample_id": "a", "generator_name": "pulse1"})}

        update(data)

        assert SAMPLES in data
        assert data["song"]["channels"]["pulse1"]["generator"] == "pulse1"
        assert _first_command(data) == {"sample_id": "a", "generator_name": "pulse1"}

    def test_document_without_samples_or_a_song_stays_the_same_shape(self) -> None:
        data = {"format_version": "1.0"}

        assert update(data) == data
