from pathlib import Path

import pytest

from sampletones_core.formats.bitphase.specification.channels import CHANNEL_LABELS
from sampletones_player.specification.nsf import ARTIST_OFFSET, NSF_MAGIC, STRING_FIELD_SIZE
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from sampletones_tools.corpus.build import Corpus
from sampletones_tools.samples import bitphase, emit, famitracker, nsf
from sampletones_tools.samples.emit import emit_samples
from tests.suite.bitphase import parse_btp
from tests.suite.famitracker import parse_ftm


def _artist(data: bytes) -> str:
    return data[ARTIST_OFFSET : ARTIST_OFFSET + STRING_FIELD_SIZE].split(b"\x00", 1)[0].decode("utf-8")


@pytest.fixture(name="corpus")
def corpus_fixture(monkeypatch: pytest.MonkeyPatch, synthetic_corpus: Corpus) -> Corpus:
    """The session's corpus, which the samples commands hand their emitter in place of a build of their own."""
    monkeypatch.setattr(emit, "build_synthetic_corpus", lambda: synthetic_corpus)
    return synthetic_corpus


class TestTheEmittersWriteTheCorpus:
    """Each format's emitter writes the files a player of that format opens."""

    def test_the_nsf_emitter_writes_every_sample_then_the_arrangement(self, corpus: Corpus, tmp_path: Path) -> None:
        written = emit_samples(tmp_path, nsf.write_samples)

        assert [path.name for path in written] == [
            *(f"{name}{EXT_FILE_NSF}" for name in corpus.catalog),
            f"{nsf.SONG_NAME}{EXT_FILE_NSF}",
        ]
        assert all(path.read_bytes()[: len(NSF_MAGIC)] == NSF_MAGIC for path in written)
        assert all(_artist(path.read_bytes()) == corpus.project.info.author for path in written)

    def test_the_famitracker_emitter_writes_one_module(self, corpus: Corpus, tmp_path: Path) -> None:
        written = emit_samples(tmp_path, famitracker.write_samples)

        assert written == [tmp_path / famitracker.MODULE_FILENAME]
        assert parse_ftm(written[0].read_bytes()).instruments

    def test_the_bitphase_emitter_writes_the_song_at_its_tempo_and_as_a_groove(
        self,
        corpus: Corpus,
        tmp_path: Path,
    ) -> None:
        written = emit_samples(tmp_path, bitphase.write_samples)

        assert written == [tmp_path / bitphase.DOCUMENT_FILENAME, tmp_path / bitphase.GROOVE_DOCUMENT_FILENAME]
        assert all(parse_btp(path.read_bytes(), list(CHANNEL_LABELS)).songs for path in written)
