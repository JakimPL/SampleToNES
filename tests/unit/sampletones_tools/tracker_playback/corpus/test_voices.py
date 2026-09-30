from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_tools.tracker_playback.corpus.spec import FrameRun, InstrumentSpec, SampleSpec
from sampletones_tools.tracker_playback.corpus.voices import build_voice, channel_frames

PULSE_FRAME: Final = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=2)
REST_FRAME: Final = PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=2)


class TestChannelFrames:
    def test_each_run_repeats_its_frame_in_order(self) -> None:
        runs = [
            FrameRun(count=2, frame=PULSE_FRAME.model_dump()),
            FrameRun(count=1, frame=REST_FRAME.model_dump()),
        ]

        assert channel_frames(ChannelName.PULSE1, runs) == [PULSE_FRAME, PULSE_FRAME, REST_FRAME]

    def test_a_frame_is_read_as_the_instruction_its_channel_takes(self) -> None:
        triangle = channel_frames(ChannelName.TRIANGLE, [FrameRun(count=1, frame={"on": True, "pitch": 48})])
        noise = channel_frames(
            ChannelName.NOISE,
            [FrameRun(count=1, frame={"on": True, "period": 3, "volume": 9, "short": True})],
        )

        assert triangle == [TriangleInstruction(on=True, pitch=48)]
        assert noise == [NoiseInstruction(on=True, period=3, volume=9, short=True)]

    def test_a_frame_the_channel_cannot_play_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            channel_frames(ChannelName.NOISE, [FrameRun(count=1, frame=PULSE_FRAME.model_dump())])


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
