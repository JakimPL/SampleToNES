from typing import Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.config.chords import ChordsConfig
from sampletones_tools.calibration.corpus.by_channel import (
    BY_CHANNEL_SUFFIX,
    UnwrittenSoundError,
    by_channel,
    with_by_channel,
    with_by_channel_catalog,
)
from sampletones_tools.calibration.corpus.chords import build_chords
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.stems import SINGLE_LINE_CAP

from ..conversions import item_named

CHORDS: Final[ChordsConfig] = ChordsConfig.model_validate(
    {
        "sounding_frames": 4,
        "silent_frames": 1,
        "chords": [
            {
                "name": "chord",
                "category": "chords-two",
                "listed": False,
                "frames": {
                    "pulse1": {"on": True, "pitch": 69, "volume": 12, "duty_cycle": 2},
                    "triangle": {"on": True, "pitch": 45},
                },
            }
        ],
    }
)
HISSING_CHORD: Final[ChordsConfig] = ChordsConfig.model_validate(
    {
        "sounding_frames": 4,
        "silent_frames": 1,
        "chords": [
            {
                "name": "hiss",
                "category": "chords-two",
                "listed": True,
                "frames": {
                    "noise": {"on": True, "period": 3, "volume": 9, "short": False},
                    "pulse2": {"on": True, "pitch": 72, "volume": 10, "duty_cycle": 1},
                },
            }
        ],
    }
)


@pytest.fixture(name="split", scope="module")
def split_fixture() -> CorpusItem:
    (chord,) = build_chords(Config(), corpus=CHORDS)
    return by_channel(chord, Config())


class TestByChannel:
    def test_each_channel_becomes_a_stem_held_to_that_channel(self, split: CorpusItem) -> None:
        assert (split.name, split.category, split.listed) == (
            f"chord{BY_CHANNEL_SUFFIX}",
            f"chords-two{BY_CHANNEL_SUFFIX}",
            False,
        )
        assert split.stems is not None
        assert [entry.settings.channels for entry in split.stems.config.entries] == [
            (ChannelName.PULSE1,),
            (ChannelName.TRIANGLE,),
        ]
        np.testing.assert_allclose(sum(split.stems.sources), split.audio, atol=1e-6)

    def test_the_sound_keeps_its_truth_and_covers_its_own_channels(self, split: CorpusItem) -> None:
        (chord,) = build_chords(Config(), corpus=CHORDS)

        assert split.truth == chord.truth
        assert split.channels == frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})

    def test_the_stems_follow_the_channel_order_and_bend_the_tonal_ones_alone(self) -> None:
        (chord,) = build_chords(Config(), corpus=HISSING_CHORD)

        stems = by_channel(chord, Config()).stems

        assert stems is not None
        assert [(entry.settings.channels, entry.settings.bends) for entry in stems.config.entries] == [
            ((ChannelName.PULSE2,), (ChannelName.PULSE2,)),
            ((ChannelName.NOISE,), ()),
        ]
        assert {entry.settings.channel_cap for entry in stems.config.entries} == {SINGLE_LINE_CAP}
        assert stems.config.hierarchy.levels == ((0, 1),)

    def test_a_sound_not_written_as_frames_is_refused(self) -> None:
        with pytest.raises(UnwrittenSoundError):
            by_channel(item_named("tone", listed=True), Config())


class TestWithByChannel:
    def test_the_written_sounds_come_first_then_each_converted_channel_by_channel(self) -> None:
        chords = build_chords(Config(), corpus=CHORDS)

        assert [item.name for item in with_by_channel(chords, Config())] == ["chord", f"chord{BY_CHANNEL_SUFFIX}"]

    def test_the_catalog_names_each_category_again_channel_by_channel(self) -> None:
        catalog = [(Family.CHORDS, "chords-two"), (Family.SEQUENCES, "sequences-melody")]

        assert with_by_channel_catalog(catalog) == [
            *catalog,
            (Family.CHORDS, f"chords-two{BY_CHANNEL_SUFFIX}"),
            (Family.SEQUENCES, f"sequences-melody{BY_CHANNEL_SUFFIX}"),
        ]

    def test_an_empty_catalog_stays_empty(self) -> None:
        assert not with_by_channel_catalog([])
