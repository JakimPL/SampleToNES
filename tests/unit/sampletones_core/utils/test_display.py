from typing import List, Optional, Tuple
from unittest.mock import Mock

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project import Project
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.utils.display import (
    NOTE_BLANK,
    NOTE_OFF,
    display_command,
    display_id,
    display_transpose,
    display_voice,
    display_voice_label,
    display_volume,
)


def _project_with_samples(count: int) -> Tuple[Project, List[Sample]]:
    project = Project.create()
    samples = [Sample(name=f"i{index}", reconstruction=Mock()) for index in range(count)]
    project.voices.extend(samples)
    return project, samples


class TestDisplaySamples:
    def test_present_shows_index(self) -> None:
        project, samples = _project_with_samples(3)
        assert (
            display_voice(
                voices=project.voices,
                voice_id=samples[0].id,
            )
            == "00"
        )
        assert (
            display_voice(
                voices=project.voices,
                voice_id=samples[2].id,
            )
            == "02"
        )

    def test_missing_and_none_are_placeholder(self) -> None:
        project, _ = _project_with_samples(1)
        assert (
            display_voice(
                voices=project.voices,
                voice_id="missing",
            )
            == ".."
        )
        assert (
            display_voice(
                voices=project.voices,
                voice_id=None,
            )
            == ".."
        )

    def test_index_follows_reorder(self) -> None:
        project, samples = _project_with_samples(3)
        first = samples[0]
        project.voices.append(project.voices.pop(0))
        assert (
            display_voice(
                voices=project.voices,
                voice_id=first.id,
            )
            == "02"
        )


class TestDisplayId:
    def test_two_digit_hexadecimal(self) -> None:
        assert display_id(10) == "0A"
        assert display_id(255) == "FF"

    def test_none_is_placeholder(self) -> None:
        assert display_id(None) == ".."


class TestDisplaySampleLabel:
    def test_combines_hex_index_and_name(self) -> None:
        assert display_voice_label(0, "Bass") == "00: Bass"

    def test_index_is_hexadecimal(self) -> None:
        assert display_voice_label(26, "Lead") == "1A: Lead"


class TestDisplayCommand:
    def test_resolves_referenced_instrument(self) -> None:
        project, samples = _project_with_samples(2)
        instrument = NoteOn(voice_id=samples[1].id)
        assert (
            display_command(
                voices=project.voices,
                command=instrument,
            )
            == "01"
        )

    def test_none_is_placeholder(self) -> None:
        project, _ = _project_with_samples(1)
        assert (
            display_command(
                voices=project.voices,
                command=None,
            )
            == ".."
        )

    def test_note_off_renders_dashes(self) -> None:
        project, _ = _project_with_samples(1)
        assert (
            display_command(
                voices=project.voices,
                command=NoteOff(),
            )
            == NOTE_OFF
        )


_TRANSPOSE_CASES = [
    (5, "+05"),
    (-5, "-05"),
    (26, "+1A"),
    (-26, "-1A"),
]


class TestDisplayTranspose:
    @pytest.mark.parametrize(("value", "expected"), _TRANSPOSE_CASES)
    def test_signed_offset_is_two_hexadecimal_digits(self, value: int, expected: str) -> None:
        assert display_transpose(value) == expected

    def test_explicit_zero_reads_as_a_zero_offset(self) -> None:
        """A row storing zero resets the channel's transpose, so the cell shows the reset."""
        assert display_transpose(0) == "+00"

    def test_absent_transpose_is_placeholder(self) -> None:
        assert display_transpose(None) == NOTE_BLANK

    def test_zero_and_absent_read_apart(self) -> None:
        assert display_transpose(0) != display_transpose(None)

    @pytest.mark.parametrize("value", [None, 0, 5, -5, 26, -26])
    def test_every_rendering_is_the_same_width(self, value: Optional[int]) -> None:
        """The grid lays transpose out in a fixed field, so every value fills it exactly."""
        assert len(display_transpose(value)) == len(NOTE_BLANK)


class TestDisplayVolume:
    def test_silent_volume_reads_as_zero(self) -> None:
        """Volume already tells a stored zero apart from an empty cell; this pins it."""
        assert display_volume(0) == "0"

    def test_absent_volume_is_placeholder(self) -> None:
        assert display_volume(None) == "."
