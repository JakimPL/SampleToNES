from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
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
        case Instrument():
            return VoiceKind.INSTRUMENT


def places_across_channels(kind: VoiceKind) -> bool:
    """Whether the tracker's sample column can place a voice of this kind.

    The column writes a voice to every channel it covers and clears the rest, which a recording
    states for itself. A hand-written instrument sounds wherever its envelopes make a frame, so the
    channel it plays on is the reader's to name and it is placed in a channel column.

    Args:
        kind: The kind of the voice being placed.

    Returns:
        bool: Whether the sample column takes it.
    """
    return kind is VoiceKind.SAMPLE
