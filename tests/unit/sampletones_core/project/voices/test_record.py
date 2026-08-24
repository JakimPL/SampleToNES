import pytest
from pydantic import TypeAdapter, ValidationError

from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.record import SampleRecord, VoiceRecord

SAMPLE_KIND = "sample"
INSTRUMENT_KIND = "instrument"

_RECORDS = TypeAdapter(VoiceRecord)


def _sample_record() -> SampleRecord:
    return SampleRecord(id="voice-id", name="Bass", reconstruction_id="reconstruction-id")


class TestTheKindADocumentNamesAVoiceBy:
    """A ``.stn`` tells its two kinds of voice apart by ``kind``, so the word is the format.

    A document written by any release names a sample ``"sample"`` and a hand-written voice
    ``"instrument"``; reading one back turns on those exact words, which is why they are stated
    here rather than read from the models.
    """

    def test_a_sample_is_written_under_its_own_word(self) -> None:
        assert _sample_record().model_dump()["kind"] == SAMPLE_KIND

    def test_an_instrument_is_written_under_its_own_word(self) -> None:
        assert Instrument(name="Pad").model_dump()["kind"] == INSTRUMENT_KIND

    def test_a_sample_record_is_read_back_as_one(self) -> None:
        restored = _RECORDS.validate_python(_sample_record().model_dump())

        assert isinstance(restored, SampleRecord)
        assert restored.reconstruction_id == "reconstruction-id"

    def test_an_instrument_record_is_read_back_as_one(self) -> None:
        restored = _RECORDS.validate_python(Instrument(name="Pad").model_dump())

        assert isinstance(restored, Instrument)
        assert restored.name == "Pad"

    def test_a_word_neither_kind_answers_to_is_refused(self) -> None:
        record = _sample_record().model_dump()
        record["kind"] = "recording"

        with pytest.raises(ValidationError):
            _RECORDS.validate_python(record)
