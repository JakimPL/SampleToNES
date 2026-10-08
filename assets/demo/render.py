from typing import Final, Mapping

import numpy as np

from assets.demo.specification import Note, Stem
from sampletones_core.audio.processing import clip_audio
from sampletones_tools.synthesis.oscillators.pulse import PulseOscillator
from sampletones_tools.synthesis.oscillators.sine import SineOscillator
from sampletones_tools.synthesis.oscillators.types import OscillatorUnion
from sampletones_tools.synthesis.voice.voice import Voice

SECONDS_PER_MINUTE: Final[float] = 60.0


def render_stem(
    stem: Stem,
    voices: Mapping[str, Voice],
    *,
    tempo: float,
    beats: float,
    sample_rate: int,
    generator: np.random.Generator,
) -> np.ndarray:
    """The stem rendered over the piece's length: every note struck where its beat falls.

    A note sounds its voice at the note's pitch for the note's length, and what runs past the end
    of the piece is cut there. Notes draw from the generator in order, so a seeded generator
    renders the stem the same every time.

    Args:
        stem: The part to render.
        voices: The voices the notes strike, by name.
        tempo: Beats per minute.
        beats: The length of the piece, in beats.
        sample_rate: Samples per second.
        generator: The random source the voices' noise draws from.

    Returns:
        np.ndarray: The unit-scale waveform, float64.
    """
    seconds_per_beat = SECONDS_PER_MINUTE / tempo
    audio = np.zeros(round(beats * seconds_per_beat * sample_rate), dtype=np.float64)
    for note in stem.notes:
        rendered = sounding(voices[note.voice], note, seconds_per_beat).render(
            sample_rate=sample_rate,
            generator=generator,
        )
        start = round(note.start * seconds_per_beat * sample_rate)
        end = min(audio.shape[0], start + rendered.shape[0])
        audio[start:end] += rendered[: end - start]

    return audio


def sounding(
    voice: Voice,
    note: Note,
    seconds_per_beat: float,
) -> Voice:
    """The voice as ``note`` strikes it: lasting the note's length, its pitched oscillators at the note's pitch.

    A note stating no length sounds the voice for the voice's own duration, and one stating no
    pitch leaves every oscillator at the frequency the voice declares.
    """
    duration = voice.duration_seconds if note.length is None else note.length * seconds_per_beat
    layers = voice.layers
    if note.pitch is not None:
        pitch = note.pitch
        layers = tuple(layer.model_copy(update={"oscillator": pitched(layer.oscillator, pitch)}) for layer in layers)

    return voice.model_copy(update={"duration_seconds": duration, "layers": layers})


def pitched(oscillator: OscillatorUnion, pitch: int) -> OscillatorUnion:
    """The oscillator sounding at the MIDI pitch ``pitch``, where its kind sounds a pitch at all."""
    match oscillator:
        case SineOscillator() | PulseOscillator():
            return oscillator.model_copy(update={"frequency": pitch})
        case _:
            return oscillator


def leveled(audio: np.ndarray, amplitude: float) -> np.ndarray:
    """The waveform scaled so its peak reaches ``amplitude``, as float32 ready to write.

    Silence stays silence, since it has no peak to scale by.
    """
    peak = float(np.abs(audio).max()) if audio.shape[0] else 0.0
    scaled = audio * (amplitude / peak) if peak > 0.0 else audio
    return clip_audio(scaled).astype(np.float32)
