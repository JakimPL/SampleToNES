from typing import Final

import pytest

from sampletones_core.configs import InstructionsLibraryConfig
from sampletones_core.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE, SAMPLE_RATES
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.library.filename.fields import InstructionsFilenameFields
from sampletones_core.library.filename.utils import (
    create_key_from_filename,
    get_display_name_from_key,
    library_key_from_filename,
)
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_shared.constants.nes import MAX_NES_FREQUENCY, MIN_NES_FREQUENCY

HASH: Final[str] = "6c2f0b1f03cdc2dff8c4ed808b4d2864"
WINDOW_SIZE: Final[int] = 4096


def make_key(
    *,
    sample_rate: int,
    nes_frequency: int,
    transformation_gamma: int,
    spectrum_method: SpectrumMethod = SpectrumMethod.FFT,
) -> InstructionLibraryKey:
    frame_length = round(sample_rate / nes_frequency)
    return InstructionLibraryKey(
        sample_rate=sample_rate,
        nes_frequency=nes_frequency,
        frame_length=frame_length,
        window_size=2 * frame_length,
        transformation_gamma=transformation_gamma,
        spectrum_method=spectrum_method,
        config_hash=HASH,
        filename=f"library_{HASH}",
    )


def _filename(*, sample_rate: int, nes_frequency: int) -> str:
    return InstructionsFilenameFields(
        sr=sample_rate,
        nf=nes_frequency,
        ws=WINDOW_SIZE,
        tg=0,
        sm=SpectrumMethod.FFT,
        ch=HASH,
    ).filename


class TestGetDisplayNameFromKey:
    def test_renders_compact_friendly_name(self) -> None:
        key = make_key(sample_rate=44100, nes_frequency=30, transformation_gamma=100)

        assert get_display_name_from_key(key) == "44.1 kHz·30 Hz·FFT·γ100"

    def test_names_the_nes_frequency_the_key_states(self) -> None:
        """At 44100 Hz, 221 Hz and 220 Hz share a frame length of 200 samples, so the name reads
        the frequency the key carries and leaves the frame length aside."""
        key = make_key(sample_rate=44100, nes_frequency=221, transformation_gamma=0)

        assert get_display_name_from_key(key) == "44.1 kHz·221 Hz·FFT·γ0"

    def test_includes_spectrum_method(self) -> None:
        key = make_key(
            sample_rate=44100,
            nes_frequency=30,
            transformation_gamma=100,
            spectrum_method=SpectrumMethod.CQT,
        )

        assert get_display_name_from_key(key) == "44.1 kHz·30 Hz·CQT·γ100"


class TestAKeyReadsTheFrequencyItsNameStates:
    """Every NES frequency in range, at every offered rate, comes back from a library's name as the
    frequency it was named with, including those whose frame lengths round onto a neighbor's."""

    @pytest.mark.parametrize("sample_rate", SAMPLE_RATES)
    def test_every_frequency_round_trips(self, sample_rate: int) -> None:
        for nes_frequency in range(MIN_NES_FREQUENCY, MAX_NES_FREQUENCY + 1):
            key = create_key_from_filename(_filename(sample_rate=sample_rate, nes_frequency=nes_frequency))
            assert key.nes_frequency == nes_frequency
            assert key.frame_length == round(sample_rate / nes_frequency)

    def test_a_key_created_from_settings_names_the_file_it_reads_back_from(self) -> None:
        config = InstructionsLibraryConfig(nes_frequency=221)
        created = InstructionLibraryKey.create(config, Window.from_config(config))

        assert create_key_from_filename(created.filename) == created


class TestAStrayNameNamesNoLibrary:
    """A library folder may hold any file; a name a library is never written under, or one stating
    settings out of a library's range, reads as no library and the listing passes it by."""

    @pytest.mark.parametrize(
        "filename",
        (
            _filename(sample_rate=MIN_SAMPLE_RATE - 1, nes_frequency=60),
            _filename(sample_rate=MAX_SAMPLE_RATE + 1, nes_frequency=60),
            _filename(sample_rate=44100, nes_frequency=MIN_NES_FREQUENCY - 1),
            _filename(sample_rate=44100, nes_frequency=MAX_NES_FREQUENCY + 1),
            "notes.ins",
            f"nf_60_sr_44100_ws_{WINDOW_SIZE}_tg_0_sm_fft_ch_{HASH}.ins",
        ),
    )
    def test_the_name_reads_as_none_and_raises_where_a_key_is_required(self, filename: str) -> None:
        assert library_key_from_filename(filename) is None

        with pytest.raises(ValueError):
            create_key_from_filename(filename)
