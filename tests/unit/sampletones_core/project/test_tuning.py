from typing import Final

import pytest

from sampletones_core.project.project import Project
from sampletones_core.project.tuning import UNTUNED_PROJECT, tuning_from_project
from sampletones_core.project.voices.sample import Sample
from sampletones_shared.music import Tuning
from tests.suite.performance import (
    make_pulse_reconstruction,
    make_triangle_reconstruction,
    project_with_sample,
    retuned_reconstruction,
)

ROWS_PER_PATTERN: Final[int] = 4
CONCERT_PITCH: Final[float] = 440.0
BAROQUE_PITCH: Final[float] = 415.0


def sampled_project() -> Project:
    project, _ = project_with_sample(
        make_pulse_reconstruction(pitch=60, count=2),
        rows_per_pattern=ROWS_PER_PATTERN,
    )
    return project


class TestTheTuningAProjectSounds:
    """A project carries no tuning of its own, so its samples state it between them."""

    def test_a_projects_sample_states_the_tuning(self) -> None:
        project = sampled_project()
        assert tuning_from_project(project) == project.voices[0].reconstruction.config.tuning

    def test_samples_agreeing_state_the_tuning_they_agree_on(self) -> None:
        project = sampled_project()
        project.voices.append(
            Sample(
                name="second",
                reconstruction=make_triangle_reconstruction(pitch=45, count=2),
            )
        )
        assert tuning_from_project(project) == Tuning(a4_frequency=CONCERT_PITCH)

    def test_a_project_holding_no_samples_sounds_the_default_tuning(self) -> None:
        """A project with nothing to sound still answers, so an empty song reaches the console."""
        assert tuning_from_project(Project.create(rows_per_pattern=ROWS_PER_PATTERN)) == UNTUNED_PROJECT

    def test_samples_that_disagree_are_refused(self) -> None:
        """One timer table sounds one tuning, so a project holding two of them names both."""
        project = sampled_project()
        project.voices.append(
            Sample(
                name="baroque",
                reconstruction=retuned_reconstruction(
                    make_triangle_reconstruction(pitch=45, count=2),
                    BAROQUE_PITCH,
                ),
            )
        )
        with pytest.raises(ValueError, match=str(BAROQUE_PITCH)):
            tuning_from_project(project)
