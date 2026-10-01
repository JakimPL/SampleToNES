from typing import List

from sampletones_core.project.project import Project
from sampletones_tools.corpus.build import build_project, build_synthetic_corpus
from sampletones_tools.samples.bitphase import at_tempo
from sampletones_tools.tracker_playback.corpus.spec import ArrangementSpec, CorpusSpec, ProjectSpec
from sampletones_tools.tracker_playback.corpus.voices import build_voice
from sampletones_tools.tracker_playback.projects import CheckedProject


def written_project(
    spec: ProjectSpec,
    corpus: CorpusSpec,
) -> CheckedProject:
    """The project a spec writes out, holding fresh copies of the corpus voices it lists.

    Args:
        spec: The project.
        corpus: The corpus whose voices the project draws on.

    Returns:
        CheckedProject: The project, with its name and purpose.

    Raises:
        KeyError: If the project lists a voice the corpus lacks, or a row names a voice the project
            leaves out.
    """
    voices = {name: build_voice(name, corpus.voices[name]) for name in spec.voices}
    return CheckedProject(
        name=spec.name,
        purpose=spec.purpose,
        project=build_project(
            voices,
            spec.module,
            spec.song,
        ),
    )


def arrangement_project(
    spec: ArrangementSpec,
    arrangement: Project,
) -> CheckedProject:
    """The synthetic corpus arrangement played at the tempo a spec names.

    Args:
        spec: The tempo, the name and the purpose.
        arrangement: The arrangement as the synthetic corpus builds it.

    Returns:
        CheckedProject: The arrangement at that tempo.
    """
    return CheckedProject(
        name=spec.name,
        purpose=spec.purpose,
        project=at_tempo(
            arrangement,
            spec.tempo,
        ),
    )


def comparison_corpus(corpus: CorpusSpec) -> List[CheckedProject]:
    """Every project a tracker playback check plays: those written out, then the reconstructed arrangement.

    Args:
        corpus: The corpus to build.

    Returns:
        List[CheckedProject]: The written projects in the order the corpus lists them, then the
            arrangement at each of its tempi.
    """
    written = [written_project(spec, corpus) for spec in corpus.projects]
    arrangement = build_synthetic_corpus().project
    return written + [arrangement_project(spec, arrangement) for spec in corpus.arrangements]
