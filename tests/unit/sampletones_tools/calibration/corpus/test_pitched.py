import math
from dataclasses import dataclass
from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.config.pitched import PitchedConfig
from sampletones_tools.calibration.config.truth import TruthConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.pitched import (
    BAND_NAME,
    BASS_LINE,
    PITCHED_CATALOG,
    VOICE_LINE,
    NoteRow,
    build_pitched,
)
from sampletones_tools.calibration.corpus.stems import SINGLE_LINE_CAP
from sampletones_tools.calibration.corpus.truth import LINE, PitchLine
from sampletones_tools.synthesis.frequency import resolve_frequency
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SAMPLE_RATE: Final[int] = 22050
FRAME_RATE: Final[int] = 60
DECAY_SECONDS: Final[float] = 0.1
AUDIBLE_DECIBELS: Final[float] = 20.0
VOICE_DEPTH_CENTS: Final[float] = 20.0
NOTE_SECONDS: Final[float] = 0.25
VOICE_PITCHES: Final[List[int]] = [57, 60, 62, 64]
CONFIG: Final[PitchedConfig] = PitchedConfig.model_validate(
    {
        "amplitude": 0.5,
        "decaying": {"frequencies": [220.0], "time_constants_seconds": [DECAY_SECONDS], "seconds": 0.5},
        "vibrato": {
            "frequencies": [220.0],
            "sawtooth_frequency": 110.0,
            "rate_hertz": 5.0,
            "depths_cents": [50.0],
            "harmonics": 8,
            "seconds": 0.5,
        },
        "line": {"pitches": [33, 45], "note_seconds": NOTE_SECONDS, "sounding_share": 0.8, "harmonics": 8},
        "voice": {
            "pitches": VOICE_PITCHES,
            "note_seconds": NOTE_SECONDS,
            "sounding_share": 0.8,
            "harmonics": 8,
            "formants": [[700.0, 130.0]],
            "formant_floor": 0.05,
            "rate_hertz": 5.0,
            "depth_cents": VOICE_DEPTH_CENTS,
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
TRUTH: Final[TruthConfig] = TruthConfig(audible_decibels=AUDIBLE_DECIBELS)
ROW: Final[NoteRow] = NoteRow(note_seconds=0.5, sounding_share=0.5, notes=3)
FRACTIONAL_NOTES: Final[int] = 3
HIGH_NOTE: Final[int] = 91
FOLDING_PARTIAL: Final[int] = 7
FOLDED_SHARE_BOUND: Final[float] = 1e-3


@pytest.fixture(name="items", scope="module")
def items_fixture() -> Dict[str, CorpusItem]:
    return {item.name: item for item in build_pitched(SAMPLE_RATE, FRAME_RATE, config=CONFIG, truth=TRUTH)}


@pytest.fixture(name="fractional_items", scope="module")
def fractional_items_fixture() -> Dict[str, CorpusItem]:
    voice = CONFIG.voice.model_copy(update={"pitches": VOICE_PITCHES[:FRACTIONAL_NOTES]})
    config = CONFIG.model_copy(update={"voice": voice})
    return {item.name: item for item in build_pitched(SAMPLE_RATE, FRAME_RATE, config=config, truth=TRUTH)}


def _line(item: CorpusItem, name: str = LINE) -> PitchLine:
    assert item.truth is not None
    return item.truth.pitches[name]


def _sounding(line: PitchLine) -> List[float]:
    return [value for value in line if value is not None]


class TestBuildPitched:
    def test_every_sound_falls_in_a_category_of_the_catalog(self, items: Dict[str, CorpusItem]) -> None:
        assert {(item.family, item.category) for item in items.values()} == set(PITCHED_CATALOG)

    def test_a_line_covers_every_frame_the_sound_reaches_into(self, items: Dict[str, CorpusItem]) -> None:
        for item in items.values():
            assert len(_line(item) if item.name != BAND_NAME else _line(item, BASS_LINE)) == math.ceil(
                len(item.audio) / SAMPLE_RATE * FRAME_RATE
            )

    def test_a_line_of_a_length_rounded_to_whole_samples_covers_every_frame_its_audio_reaches(
        self, fractional_items: Dict[str, CorpusItem]
    ) -> None:
        voice = fractional_items["vowel-melody"]

        assert len(voice.audio) * FRAME_RATE % SAMPLE_RATE
        assert len(_line(voice)) == math.ceil(len(voice.audio) * FRAME_RATE / SAMPLE_RATE)

    def test_a_decay_sounds_its_pitch_until_it_falls_below_the_audible_range(
        self, items: Dict[str, CorpusItem]
    ) -> None:
        line = _line(items["sine-decay-220hz-0.1s"])
        heard_until = DECAY_SECONDS * AUDIBLE_DECIBELS / 20.0 * math.log(10.0)
        last_heard = math.floor(heard_until * FRAME_RATE - 0.5)

        assert line[: last_heard + 1] == (220.0,) * (last_heard + 1)
        assert set(line[last_heard + 1 :]) == {None}

    def test_a_vibrato_line_swings_around_its_frequency(self, items: Dict[str, CorpusItem]) -> None:
        line = _sounding(_line(items["sine-vibrato-220hz-50c"]))

        assert min(line) < 220.0 < max(line)

    def test_a_line_holds_each_note_and_falls_silent_between_them(self, items: Dict[str, CorpusItem]) -> None:
        line = _line(items["saw-line"])

        assert line[0] == pytest.approx(55.0)
        assert None in line
        assert line[int(0.35 * FRAME_RATE)] == pytest.approx(110.0)

    def test_the_vowel_melody_follows_the_swinging_fundamental_of_each_note(self, items: Dict[str, CorpusItem]) -> None:
        line = _line(items["vowel-melody"])
        swing = 2 ** (VOICE_DEPTH_CENTS / 1200.0)
        note_frames = int(NOTE_SECONDS * FRAME_RATE)

        for index, pitch in enumerate(VOICE_PITCHES):
            heard = _sounding(line[index * note_frames : (index + 1) * note_frames])
            center = resolve_frequency(pitch)
            assert heard and all(center / swing <= value <= center * swing for value in heard)
        assert len(set(_sounding(line))) > 3

    def test_the_vowel_melody_builds_the_partials_staying_below_the_nyquist_limit_through_the_swing(self) -> None:
        frequency = resolve_frequency(HIGH_NOTE)
        swing = 2 ** (VOICE_DEPTH_CENTS / 1200.0)
        assert FOLDING_PARTIAL * frequency < SAMPLE_RATE / 2 < FOLDING_PARTIAL * frequency * swing
        voice = CONFIG.voice.model_copy(update={"pitches": [HIGH_NOTE]})
        items = build_pitched(SAMPLE_RATE, FRAME_RATE, config=CONFIG.model_copy(update={"voice": voice}), truth=TRUTH)
        audio = next(item for item in items if item.name == "vowel-melody").audio

        power = np.abs(np.fft.rfft(audio)) ** 2
        bins = np.fft.rfftfreq(len(audio), 1.0 / SAMPLE_RATE)
        highest_kept = (FOLDING_PARTIAL - 1) * frequency * swing
        above_kept = bins > highest_kept + frequency / 2

        assert float(np.sum(power[above_kept]) / np.sum(power)) < FOLDED_SHARE_BOUND

    def test_every_sound_peaks_at_the_amplitude(self, items: Dict[str, CorpusItem]) -> None:
        for item in items.values():
            assert float(abs(item.audio).max()) == pytest.approx(CONFIG.amplitude, rel=1e-3)


class TestBand:
    def test_the_band_holds_the_bass_the_melody_and_the_drums_as_stems_adding_up_to_it(
        self,
        items: Dict[str, CorpusItem],
    ) -> None:
        band = items[BAND_NAME]

        assert band.stems is not None and len(band.stems.sources) == 3
        np.testing.assert_allclose(sum(band.stems.sources), band.audio, atol=1e-6)

    def test_each_part_is_one_line_on_its_own_channels(self, items: Dict[str, CorpusItem]) -> None:
        band = items[BAND_NAME]

        assert band.stems is not None
        assert [entry.settings.channels for entry in band.stems.config.entries] == [
            (ChannelName.TRIANGLE,),
            (ChannelName.PULSE1, ChannelName.PULSE2),
            (ChannelName.NOISE,),
        ]
        assert {entry.settings.channel_cap for entry in band.stems.config.entries} == {SINGLE_LINE_CAP}
        assert band.channels == frozenset(ChannelName.items())

    def test_the_two_lines_run_to_the_band_s_length_the_shorter_in_silence(self, items: Dict[str, CorpusItem]) -> None:
        band = items[BAND_NAME]
        bass, voice = _line(items["saw-line"]), _line(items["vowel-melody"])

        assert band.truth is not None and set(band.truth.pitches) == {BASS_LINE, VOICE_LINE}
        assert len(bass) < len(voice)
        assert _line(band, BASS_LINE) == bass + (None,) * (len(voice) - len(bass))
        assert _line(band, VOICE_LINE) == voice

    def test_the_band_s_lines_count_the_frames_its_lines_count(self, fractional_items: Dict[str, CorpusItem]) -> None:
        band, voice = fractional_items[BAND_NAME], _line(fractional_items["vowel-melody"])

        assert _line(band, VOICE_LINE) == voice
        assert len(_line(band, BASS_LINE)) == len(voice)


class TestNoteRow(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        time: float
        note: int
        sounding: bool

    test_cases = (
        TestCase(time=0.0, note=0, sounding=True, label="the first note's start"),
        TestCase(time=0.2, note=0, sounding=True, label="within the first note's share"),
        TestCase(time=0.3, note=0, sounding=False, label="the first note's rest"),
        TestCase(time=0.5, note=1, sounding=True, label="the second note's start"),
        TestCase(time=1.4, note=2, sounding=False, label="the last note's rest"),
        TestCase(time=1.6, note=2, sounding=False, label="past the row"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_time_falls_in_one_note_sounding_its_share(self, test_case: TestCase) -> None:
        times = np.array([test_case.time])

        assert int(ROW.note_at(times)[0]) == test_case.note
        assert bool(ROW.sounding_at(times)[0]) is test_case.sounding

    def test_the_row_lasts_its_notes_times_their_length(self) -> None:
        assert ROW.seconds == pytest.approx(1.5)

    def test_a_gate_sounds_its_note_for_its_share(self) -> None:
        gate = ROW.gate(1)

        assert (gate.start_seconds, gate.end_seconds) == pytest.approx((0.5, 0.75))
