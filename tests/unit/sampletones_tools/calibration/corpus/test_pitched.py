from typing import Dict, Final, List

import pytest

from sampletones_tools.calibration.config.pitched import PitchedConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.pitched import LINE, PITCHED_CATALOG, build_pitched

SAMPLE_RATE: Final[int] = 22050
FRAME_RATE: Final[int] = 60
CONFIG: Final[PitchedConfig] = PitchedConfig.model_validate(
    {
        "amplitude": 0.5,
        "audible_decibels": 20.0,
        "decaying": {"frequencies": [220.0], "time_constants_seconds": [0.1], "seconds": 0.5},
        "vibrato": {
            "frequencies": [220.0],
            "sawtooth_frequency": 110.0,
            "rate_hertz": 5.0,
            "depths_cents": [50.0],
            "harmonics": 8,
            "seconds": 0.5,
        },
        "line": {"pitches": [33, 45], "note_seconds": 0.25, "sounding_share": 0.8, "harmonics": 8},
        "voice": {
            "pitches": [57, 60],
            "note_seconds": 0.25,
            "sounding_share": 0.8,
            "harmonics": 8,
            "formants": [[700.0, 130.0]],
            "formant_floor": 0.05,
            "rate_hertz": 5.0,
            "depth_cents": 20.0,
        },
        "pluck": {"frequencies": [220.0], "time_constant_seconds": 0.3, "harmonics": 6, "seconds": 0.5},
        "band": {
            "bass_level": 0.6,
            "voice_level": 0.5,
            "drums_level": 0.6,
            "hits": [{"period_seconds": 0.25, "decay_seconds": 0.05, "delay_seconds": 0.0, "level": 1.0}],
        },
    }
)


@pytest.fixture(name="items", scope="module")
def items_fixture() -> Dict[str, CorpusItem]:
    return {item.name: item for item in build_pitched(SAMPLE_RATE, FRAME_RATE, config=CONFIG)}


def _line(item: CorpusItem) -> List[object]:
    assert item.truth is not None
    return list(item.truth.pitches[LINE])


class TestBuildPitched:
    def test_every_sound_falls_in_a_category_of_the_catalog(self, items: Dict[str, CorpusItem]) -> None:
        assert {(item.family, item.category) for item in items.values()} == set(PITCHED_CATALOG)

    def test_a_decay_sounds_its_pitch_until_it_falls_below_the_audible_range(
        self, items: Dict[str, CorpusItem]
    ) -> None:
        line = _line(items["sine-decay-220hz-0.1s"])

        assert line[0] == 220.0
        assert line[-1] is None

    def test_a_vibrato_line_swings_around_its_frequency(self, items: Dict[str, CorpusItem]) -> None:
        line = [value for value in _line(items["sine-vibrato-220hz-50c"]) if isinstance(value, float)]

        assert min(line) < 220.0 < max(line)

    def test_a_line_holds_each_note_and_falls_silent_between_them(self, items: Dict[str, CorpusItem]) -> None:
        line = _line(items["saw-line"])

        assert line[0] == pytest.approx(55.0)
        assert None in line
        assert line[int(0.35 * FRAME_RATE)] == pytest.approx(110.0)

    def test_every_sound_peaks_at_the_amplitude(self, items: Dict[str, CorpusItem]) -> None:
        for item in items.values():
            assert float(abs(item.audio).max()) == pytest.approx(CONFIG.amplitude, rel=1e-3)


class TestBand:
    def test_the_band_holds_the_bass_the_melody_and_the_drums_as_stems_with_two_lines(
        self,
        items: Dict[str, CorpusItem],
    ) -> None:
        band = items["band"]

        assert band.stems is not None and len(band.stems.sources) == 3
        assert band.truth is not None and set(band.truth.pitches) == {"bass", "voice"}
        assert all(len(line) == len(band.truth.pitches["bass"]) for line in band.truth.pitches.values())
