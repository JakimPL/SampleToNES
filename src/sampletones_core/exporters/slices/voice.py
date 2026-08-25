from dataclasses import dataclass
from typing import Iterator, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.project.project import Project
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion, voice_channels


@dataclass(frozen=True)
class VoiceSlice:
    """What one channel of one voice plays, in the envelope terms every backend reads.

    Attributes:
        voice: The voice the slice came from.
        channel: The NES channel the slice covers.
        features: The per-dimension envelopes describing the slice.
    """

    voice: VoiceUnion
    channel: ChannelName
    features: Features

    @property
    def instrument_name(self) -> str:
        """The exported instrument's name, naming both its voice and its channel."""
        return instrument_slice_name(self.voice.name, self.channel)

    @property
    def key(self) -> Tuple[str, ChannelName]:
        """The identity a pattern row references the slice by."""
        return (self.voice.id, self.channel)


def sample_slices(sample: Sample) -> Iterator[VoiceSlice]:
    """What each channel of a recording plays, one slice per channel its conversion found frames for.

    Args:
        sample: The sample being exported.

    Yields:
        VoiceSlice: What each of its playing channels plays.
    """
    features_by_channel = sample.reconstruction.export()
    for channel in ChannelName.items():
        features = features_by_channel[channel]
        if features.has_frames:
            yield VoiceSlice(
                voice=sample,
                channel=channel,
                features=features,
            )


def instrument_slices(instrument: Instrument) -> Iterator[VoiceSlice]:
    """What each channel of a hand-written voice plays, each reading the one envelope set its way.

    Args:
        instrument: The voice being exported.

    Yields:
        VoiceSlice: What each channel its envelopes make a frame for plays.
    """
    for channel in voice_channels(instrument):
        yield VoiceSlice(
            voice=instrument,
            channel=channel,
            features=instrument.features(channel),
        )


def voice_slices(voice: VoiceUnion) -> Iterator[VoiceSlice]:
    """What each channel of one voice plays, whichever kind the voice is.

    Args:
        voice: The voice being exported.

    Yields:
        VoiceSlice: What each of its playing channels plays.
    """
    match voice:
        case Sample():
            yield from sample_slices(voice)
        case Instrument():
            yield from instrument_slices(voice)


def iterate_voice_slices(project: Project) -> Iterator[VoiceSlice]:
    """Walks what every channel of every voice plays, in voice order then channel order.

    A voice contributes one slice per channel it sounds on, so a sample yields one to four and an
    instrument yields one per channel its envelopes make a frame for. Each voice is read once, so a
    caller reads a reconstruction's envelopes at a single cost.

    Args:
        project: The project whose voices are exported.

    Yields:
        VoiceSlice: What each channel of each voice plays.
    """
    for voice in project.voices:
        yield from voice_slices(voice)
