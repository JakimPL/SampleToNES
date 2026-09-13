from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, List

from sampletones_tools.corpus.build import Corpus, build_corpus

Emitter = Callable[[Corpus, Path], List[Path]]


def emit_samples(output: Path, emitter: Emitter) -> List[Path]:
    """Builds the synthetic corpus and hands it to an emitter writing into ``output``.

    Args:
        output: The directory the files are written into, created when missing.
        emitter: The writer of one format.

    Returns:
        List[Path]: The files the emitter wrote.
    """
    with TemporaryDirectory() as recordings:
        corpus = build_corpus(Path(recordings))

    output.mkdir(parents=True, exist_ok=True)
    return emitter(corpus, output)
