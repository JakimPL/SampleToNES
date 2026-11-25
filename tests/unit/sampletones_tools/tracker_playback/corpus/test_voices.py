from typing import Final

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import PulseInstruction
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_tools.corpus.written import FrameRun
from sampletones_tools.tracker_playback.corpus.spec import InstrumentSpec, SampleSpec
from sampletones_tools.tracker_playback.corpus.voices import build_voice

PULSE_FRAME: Final = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=2)


class TestBuildVoice:
    def test_a_sample_plays_the_frames_it_writes_on_its_channels(self) -> None:
        spec = SampleSpec(
            kind="sample",
            channels={ChannelName.PULSE2: [FrameRun(count=3, frame=PULSE_FRAME.model_dump())]},
        )

        voice = build_voice("tone", spec)

        assert isinstance(voice, Sample)
        assert voice.name == "tone"
        assert voice.reconstruction.playing_channels == (ChannelName.PULSE2,)
        assert list(voice.reconstruction.instructions[ChannelName.PULSE2]) == [PULSE_FRAME] * 3

    def test_an_instrument_carries_its_envelopes_and_references(self) -> None:
        envelopes = InstrumentEnvelopes(volume=Envelope[int](items=(15, 0)))
        spec = InstrumentSpec(kind="instrument", initial_pitch=57, initial_period=4, envelopes=envelopes)

        voice = build_voice("pluck", spec)

        assert isinstance(voice, Instrument)
        assert (voice.name, voice.initial_pitch, voice.initial_period) == ("pluck", 57, 4)
        assert voice.envelopes.envelope(FeatureKey.VOLUME).items == (15, 0)
