from .envelopes.exponential_decay import ExponentialDecayEnvelope
from .envelopes.linear_attack import LinearAttackEnvelope
from .envelopes.linear_ramp import LinearRampEnvelope
from .envelopes.types import EnvelopeUnion
from .filters.butterworth_highpass import ButterworthHighpassFilter
from .filters.types import FilterUnion
from .frequency import FrequencySpec, resolve_frequency
from .oscillators.exponential_glide import ExponentialGlideOscillator
from .oscillators.geometric_sweep import GeometricSweepOscillator
from .oscillators.pulse import DutyCycle, PulseOscillator
from .oscillators.sine import SineOscillator
from .oscillators.types import OscillatorUnion
from .oscillators.walk_noise import WalkNoiseOscillator
from .oscillators.white_noise import WhiteNoiseOscillator
from .protocols import AudioFilter, Envelope, Oscillator
from .voice.layer import Layer
from .voice.voice import Voice

__all__ = [
    "AudioFilter",
    "ButterworthHighpassFilter",
    "DutyCycle",
    "Envelope",
    "EnvelopeUnion",
    "ExponentialDecayEnvelope",
    "ExponentialGlideOscillator",
    "FilterUnion",
    "FrequencySpec",
    "GeometricSweepOscillator",
    "Layer",
    "LinearAttackEnvelope",
    "LinearRampEnvelope",
    "Oscillator",
    "OscillatorUnion",
    "PulseOscillator",
    "SineOscillator",
    "Voice",
    "WalkNoiseOscillator",
    "WhiteNoiseOscillator",
    "resolve_frequency",
]
