from typing import Any, Dict

import pytest

from sampletones_core.compatibility.fields import (
    KIND,
    KIND_SAMPLE,
    KIND_STEP,
    NAME,
    PITCH,
    SAMPLES,
    TRANSPOSE,
    VALUE,
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


def _song_of_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"song": {"channels": {"pulse1": {"generator": "pulse1", "patterns": {"0": {"rows": [row]}}}}}}


def _first_row(data: Dict[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = data["song"]["channels"]["pulse1"]["patterns"]["0"]["rows"][0]
    return row


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


class TestARowsTransposeBecomesAStep:
    """A 1.0 row wrote its pitch as a bare transpose, which 1.1 reads as a step from the voice's reference."""

    @pytest.mark.parametrize("transpose", [3, 0, -12])
    def test_a_transpose_becomes_a_step_of_the_same_value(self, transpose: int) -> None:
        upgraded = update(_song_of_row({TRANSPOSE: transpose, "volume": 8}))

        row = _first_row(upgraded)
        assert row[PITCH] == {KIND: KIND_STEP, VALUE: transpose}
        assert TRANSPOSE not in row
        assert row["volume"] == 8

    def test_an_empty_transpose_leaves_the_row_without_a_pitch(self) -> None:
        row = _first_row(update(_song_of_row({TRANSPOSE: None})))

        assert PITCH not in row
        assert TRANSPOSE not in row

    def test_a_row_without_the_key_stays_as_it_stands(self) -> None:
        assert _first_row(update(_song_of_row({"volume": 8}))) == {"volume": 8}

    def test_a_row_carrying_a_command_and_a_transpose_has_both_reshaped(self) -> None:
        row = _first_row(
            update(_song_of_row({"command": {"sample_id": "a", "generator_name": "pulse1"}, TRANSPOSE: 5}))
        )

        assert row == {"command": {VOICE_ID: "a"}, PITCH: {KIND: KIND_STEP, VALUE: 5}}

    def test_the_input_row_is_left_untouched(self) -> None:
        data = _song_of_row({TRANSPOSE: 5})

        update(data)

        assert _first_row(data) == {TRANSPOSE: 5}
