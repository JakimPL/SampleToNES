from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_tools.corpus.written import written_runs
from sampletones_tools.tracker_playback.corpus.spec import InstrumentSpec, SampleSpec, VoiceSpec


def build_voice(
    name: str,
    spec: VoiceSpec,
) -> VoiceUnion:
    """The voice a spec describes: a sample playing its written frames, or an instrument.

    Args:
        name: The voice's name.
        spec: What the voice plays.

    Returns:
        VoiceUnion: The voice.
    """
    match spec:
        case SampleSpec():
            return Sample(name=name, reconstruction=written_runs(spec.channels))
        case InstrumentSpec():
            return Instrument(
                name=name,
                initial_pitch=spec.initial_pitch,
                initial_period=spec.initial_period,
                envelopes=spec.envelopes,
            )
