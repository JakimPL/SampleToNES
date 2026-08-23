from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.shape import Shape
from sampletones_core.project.voices.voice import VoiceUnion


def voice_kind(voice: VoiceUnion) -> VoiceKind:
    """Which of the two kinds a voice is, as the list marks it.

    Args:
        voice: The voice being listed.

    Returns:
        VoiceKind: The kind the row shows and its gestures follow from.
    """
    match voice:
        case Sample():
            return VoiceKind.SAMPLE
        case Shape():
            return VoiceKind.SHAPE
