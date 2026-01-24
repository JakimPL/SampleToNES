from enum import Enum


class SpectrumMethod(Enum):
    FFT = "fft"
    LOG_SPACED_FFT = "log_spaced_fft"
    CQT = "cqt"
