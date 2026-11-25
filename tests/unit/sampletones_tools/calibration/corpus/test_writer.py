from pathlib import Path
from typing import List

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem, StemsSources
from sampletones_tools.calibration.corpus.writer import write_corpus


class TestWriteCorpus:
    def test_writes_one_wav_per_item(
        self,
        corpus_items: List[CorpusItem],
        tmp_path: Path,
        sample_rate: int,
    ) -> None:
        paths = write_corpus(corpus_items, tmp_path / "corpus", sample_rate)
        assert set(paths) == {item.name for item in corpus_items}
        for (path,) in paths.values():
            assert path.exists()
            assert path.suffix == ".wav"

    def test_a_sound_held_as_stems_writes_one_wav_per_stem(self, tmp_path: Path, sample_rate: int) -> None:
        sources = (np.zeros(8, dtype=np.float32), np.ones(8, dtype=np.float32) / 4)
        config = StemsConfig(
            entries=tuple(
                StemEntry(id=index, settings=StemSettings.covering([channel]))
                for index, channel in enumerate((ChannelName.PULSE1, ChannelName.NOISE))
            ),
            hierarchy=StemsHierarchy(levels=((0, 1),)),
        )
        item = CorpusItem(
            name="band",
            family=Family.COMPOSITES,
            category="composites-band",
            listed=True,
            audio=sum(sources),
            truth=None,
            channels=None,
            stems=StemsSources(sources=sources, config=config),
        )

        (paths,) = write_corpus([item], tmp_path, sample_rate).values()

        assert [path.name for path in paths] == ["band-stem0.wav", "band-stem1.wav"]
