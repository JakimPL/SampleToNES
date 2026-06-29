from typing import Dict, Final

from sampletones_core.constants.enums import SpectrumMethod

DISPLAY_SEPARATOR: Final[str] = "·"
GAMMA_PREFIX: Final[str] = "γ"
DISPLAY_HASH_LENGTH: Final[int] = 7

HERTZ_UNIT: Final[str] = "Hz"
KILOHERTZ_UNIT: Final[str] = "kHz"
SAMPLES_PER_KILOHERTZ: Final[int] = 1000

SPECTRUM_METHOD_LABELS: Final[Dict[SpectrumMethod, str]] = {
    SpectrumMethod.FFT: "FFT",
    SpectrumMethod.LOG_SPACED_FFT: "LogFFT",
    SpectrumMethod.CQT: "CQT",
}
SPECTRUM_METHOD_BY_LABEL: Final[Dict[str, SpectrumMethod]] = {
    label: method for method, label in SPECTRUM_METHOD_LABELS.items()
}


def format_sample_rate(sample_rate: int) -> str:
    """Renders a sample rate in kilohertz, dropping a redundant ``.0`` (e.g. ``44.1 kHz``, ``48 kHz``)."""
    kilohertz = sample_rate / SAMPLES_PER_KILOHERTZ
    if kilohertz == int(kilohertz):
        return f"{int(kilohertz)} {KILOHERTZ_UNIT}"

    return f"{kilohertz:g} {KILOHERTZ_UNIT}"


def format_nes_frequency(nes_frequency: int) -> str:
    return f"{nes_frequency} {HERTZ_UNIT}"


def format_spectrum_method(method: SpectrumMethod) -> str:
    return SPECTRUM_METHOD_LABELS[method]


def short_hash(config_hash: str) -> str:
    return config_hash[:DISPLAY_HASH_LENGTH]
