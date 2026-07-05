from pathlib import Path
from typing import List

from sampletones_core.calibration.corpus.item import CorpusItem
from sampletones_core.calibration.corpus.writer import write_corpus


class TestWriteCorpus:
    def test_writes_one_wav_per_item(
        self,
        corpus_items: List[CorpusItem],
        tmp_path: Path,
        sample_rate: int,
    ) -> None:
        paths = write_corpus(corpus_items, tmp_path / "corpus", sample_rate)
        assert set(paths) == {item.name for item in corpus_items}
        for path in paths.values():
            assert path.exists()
            assert path.suffix == ".wav"
