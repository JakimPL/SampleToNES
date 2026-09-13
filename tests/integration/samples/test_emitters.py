from pathlib import Path
from typing import Dict

import pytest

from sampletones_core.formats.bitphase.specification.channels import CHANNEL_LABELS
from sampletones_core.project.project import Project
from sampletones_core.project.voices.sample import Sample
from sampletones_player.specification.nsf import NSF_MAGIC
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from sampletones_tools.corpus.build import Corpus
from sampletones_tools.samples import bitphase, famitracker, nsf
from tests.suite.bitphase import parse_btp
from tests.suite.famitracker import parse_ftm


@pytest.fixture(scope="module")
def corpus(instrument_catalog: Dict[str, Sample], integration_project: Project) -> Corpus:
    """The session's catalog and arrangement, as the emitters are handed them."""
    return Corpus(catalog=instrument_catalog, project=integration_project)


class TestTheEmittersWriteTheCorpus:
    """Each format's emitter writes the files a player of that format opens."""

    def test_the_nsf_emitter_writes_every_sample_then_the_arrangement(self, corpus: Corpus, tmp_path: Path) -> None:
        written = nsf.write_samples(corpus, tmp_path)

        assert [path.name for path in written] == [
            *(f"{name}{EXT_FILE_NSF}" for name in corpus.catalog),
            f"{nsf.SONG_NAME}{EXT_FILE_NSF}",
        ]
        assert all(path.read_bytes()[: len(NSF_MAGIC)] == NSF_MAGIC for path in written)

    def test_the_famitracker_emitter_writes_one_module(self, corpus: Corpus, tmp_path: Path) -> None:
        written = famitracker.write_samples(corpus, tmp_path)

        assert written == [tmp_path / famitracker.MODULE_FILENAME]
        assert parse_ftm(written[0].read_bytes()).instruments

    def test_the_bitphase_emitter_writes_the_song_at_its_tempo_and_as_a_groove(
        self,
        corpus: Corpus,
        tmp_path: Path,
    ) -> None:
        written = bitphase.write_samples(corpus, tmp_path)

        assert written == [tmp_path / bitphase.DOCUMENT_FILENAME, tmp_path / bitphase.GROOVE_DOCUMENT_FILENAME]
        assert all(parse_btp(path.read_bytes(), list(CHANNEL_LABELS)).songs for path in written)
