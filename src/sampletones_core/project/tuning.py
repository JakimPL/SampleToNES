from typing import Final, Set

from sampletones_core.project.project import Project
from sampletones_shared.music import Tuning

UNTUNED_PROJECT: Final[Tuning] = Tuning()


def _named(tuning: Tuning) -> str:
    return f"A{tuning.a4_pitch} at {tuning.a4_frequency} Hz"


def tuning_from_project(project: Project) -> Tuning:
    """Where concert pitch sits for a whole project, which its samples state together.

    A project carries no tuning of its own: each sample was reconstructed against one, and a
    format sounding those pitches itself — the console player reaching them through timer values
    — measures the whole song from a single tuning. The samples state it by agreeing on it, and
    a project holding none takes the tuning a reconstruction is built against by default.

    Args:
        project: The project whose voices state the tuning.

    Returns:
        Tuning: The tuning every sample of the project was reconstructed against.

    Raises:
        ValueError: If the samples were reconstructed against tunings that differ, which one
            timer table sounds only one of.
    """
    tunings: Set[Tuning] = {voice.reconstruction.config.tuning for voice in project.voices}
    if not tunings:
        return UNTUNED_PROJECT

    if len(tunings) > 1:
        stated = ", ".join(sorted(_named(tuning) for tuning in tunings))
        raise ValueError(f"a project sounds one tuning, and its samples were reconstructed at {stated}")

    return tunings.pop()
