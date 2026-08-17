from collections import Counter
from typing import Dict, Final, Sequence, Tuple

from sampletones_core.constants.enums import SpectrumMethod
from sampletones_shared.constants.symbols import HASH

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


def format_transformation_gamma(transformation_gamma: int) -> str:
    """Marks a transformation gamma with ``γ`` (e.g. ``γ0``)."""
    return f"{GAMMA_PREFIX}{transformation_gamma}"


def format_frequencies(sample_rate: int, nes_frequency: int) -> str:
    """Renders the rates a reconstruction runs at, audio before frame (e.g. ``44.1 kHz·30 Hz``)."""
    return DISPLAY_SEPARATOR.join(
        [
            format_sample_rate(sample_rate),
            format_nes_frequency(nes_frequency),
        ],
    )


def format_transformation(
    spectrum_method: SpectrumMethod,
    transformation_gamma: int,
) -> str:
    """Renders the spectrum a library was built from, method before gamma (e.g. ``FFT·γ0``)."""
    return DISPLAY_SEPARATOR.join(
        [
            format_spectrum_method(spectrum_method),
            format_transformation_gamma(transformation_gamma),
        ],
    )


def short_hash(config_hash: str) -> str:
    return config_hash[:DISPLAY_HASH_LENGTH]


def disambiguated_display_name(name: str, config_hash: str) -> str:
    """Appends the short config hash, marked with ``#``, so colliding names stay distinct."""
    return f"{name}{DISPLAY_SEPARATOR}{HASH}{short_hash(config_hash)}"


def unique_display_names(entries: Sequence[Tuple[str, str]]) -> Tuple[str, ...]:
    """Answers labels that tell one group of siblings apart, given ``(name, config hash)`` pairs.

    A name held by a single entry stands as it is. A name shared by several entries takes the short
    config hash on every one of them, so each sibling states the configuration that distinguishes
    it. The answer is index-aligned with ``entries``.
    """
    occurrences = Counter(name for name, _ in entries)
    return tuple(
        name if occurrences[name] == 1 else disambiguated_display_name(name, config_hash)
        for name, config_hash in entries
    )
