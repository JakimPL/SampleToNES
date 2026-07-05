from typing import List, Tuple
from unittest.mock import Mock

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project import Project
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.utils.display import (
    NOTE_OFF,
    display_command,
    display_id,
    display_sample,
    display_sample_label,
)


def _project_with_samples(count: int) -> Tuple[Project, List[Sample]]:
    project = Project.create()
    samples = [Sample(name=f"i{index}", reconstruction=Mock()) for index in range(count)]
    project.samples.extend(samples)
    return project, samples


class TestDisplaySamples:
    def test_present_shows_index(self) -> None:
        project, samples = _project_with_samples(3)
        assert (
            display_sample(
                samples=project.samples,
                sample_id=samples[0].id,
            )
            == "00"
        )
        assert (
            display_sample(
                samples=project.samples,
                sample_id=samples[2].id,
            )
            == "02"
        )

    def test_missing_and_none_are_placeholder(self) -> None:
        project, _ = _project_with_samples(1)
        assert (
            display_sample(
                samples=project.samples,
                sample_id="missing",
            )
            == ".."
        )
        assert (
            display_sample(
                samples=project.samples,
                sample_id=None,
            )
            == ".."
        )

    def test_index_follows_reorder(self) -> None:
        project, samples = _project_with_samples(3)
        first = samples[0]
        project.samples.append(project.samples.pop(0))
        assert (
            display_sample(
                samples=project.samples,
                sample_id=first.id,
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
        assert display_sample_label(0, "Bass") == "00: Bass"

    def test_index_is_hexadecimal(self) -> None:
        assert display_sample_label(26, "Lead") == "1A: Lead"


class TestDisplayCommand:
    def test_resolves_referenced_instrument(self) -> None:
        project, samples = _project_with_samples(2)
        instrument = Instrument(
            sample_id=samples[1].id,
            generator_name=GeneratorName.PULSE1,
        )
        assert (
            display_command(
                samples=project.samples,
                command=instrument,
            )
            == "01"
        )

    def test_none_is_placeholder(self) -> None:
        project, _ = _project_with_samples(1)
        assert (
            display_command(
                samples=project.samples,
                command=None,
            )
            == ".."
        )

    def test_note_off_renders_dashes(self) -> None:
        project, _ = _project_with_samples(1)
        assert (
            display_command(
                samples=project.samples,
                command=NoteOff(),
            )
            == NOTE_OFF
        )
