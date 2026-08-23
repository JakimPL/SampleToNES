from typing import Callable

from sampletones_application.constants.instruments import INSTRUMENT_CHANNEL
from sampletones_application.logic.export.instrument.source import (
    exportable_instrument,
    sounding_channel,
    voice_entries,
    voice_instrument,
    voice_instrument_channels,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.request import InstrumentSource
from sampletones_core.project.project import Project
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.music import Tuning
from tests.suite.sequencer import sample_reconstruction


def _project(*voices: VoiceUnion) -> Project:
    project = Project.create()
    for voice in voices:
        project.voices.append(voice)

    return project


class TestWhatAVoiceOffers:
    """One rule answers what a voice contributes, so both kinds are exported the same way."""

    def test_a_written_instrument_offers_one(self) -> None:
        """One set of envelopes every channel reads is one instrument, as a module holds it."""
        voice = new_instrument("Lead")

        assert len(voice_entries(voice)) == 1

    def test_a_written_instrument_is_named_after_itself(self) -> None:
        voice = new_instrument("Lead")

        assert voice_entries(voice)[0].name == "Lead"

    def test_a_sample_offers_one_per_channel_that_plays(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())
        playing = sample.reconstruction.playing_channels

        assert [entry.channel for entry in voice_entries(sample)] == list(playing)

    def test_a_samples_slice_is_named_for_its_channel(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())

        assert all(entry.name.startswith("Bass") for entry in voice_entries(sample))

    def test_both_kinds_answer_with_the_same_shape(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """Whatever produced the envelopes is settled here, so one export path takes both."""
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())
        written = new_instrument("Lead")
        project = _project(sample, written)

        sources = [exportable_instrument(project, entry).source for entry in voice_entries(sample)]
        sources += [exportable_instrument(project, entry).source for entry in voice_entries(written)]

        assert all(isinstance(source, InstrumentSource) for source in sources)

    def test_the_project_states_the_rate_and_the_tuning(self) -> None:
        voice = new_instrument("Lead")
        project = _project(voice)

        source = exportable_instrument(project, voice_entries(voice)[0]).source

        assert source.nes_frequency == project.settings.nes_frequency
        assert source.tuning == Tuning()

    def test_a_voice_with_nothing_written_offers_nothing(self) -> None:
        sample = Sample(name="Silent", reconstruction=sample_reconstruction(set()))

        assert voice_entries(sample) == ()


class TestWhichChannelAFileSoundsItOn:
    """A written file plays its instrument somewhere, and the entry states where or leaves it open."""

    def test_a_samples_slice_sounds_on_the_channel_it_was_reconstructed_for(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())

        for entry in voice_entries(sample):
            assert sounding_channel(entry) is entry.channel

    def test_a_written_instrument_sounds_where_the_app_reads_it(self) -> None:
        """Its envelopes name no channel, so the file plays them where its editor shows them."""
        voice = new_instrument("Lead")

        assert sounding_channel(voice_entries(voice)[0]) is INSTRUMENT_CHANNEL

    def test_a_written_instrument_is_measured_against_the_root_that_channel_reads(self) -> None:
        """The channel it is sounded on and the reference its envelopes carry are one answer."""
        voice = new_instrument("Lead")
        entry = voice_entries(voice)[0]

        assert entry.features.initial_pitch == voice.reference(sounding_channel(entry))


class TestWhatOneVoiceIsAskedFor:
    """A menu asks what a voice offers, and a click asks for one of them by the channel it named."""

    def test_a_sample_offers_each_channel_that_plays(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())
        project = _project(sample)

        assert voice_instrument_channels(project, sample.id) == tuple(sample.reconstruction.playing_channels)

    def test_a_written_instrument_offers_one_naming_no_channel(self) -> None:
        voice = new_instrument("Lead")

        assert voice_instrument_channels(_project(voice), voice.id) == (None,)

    def test_a_voice_the_pool_lost_offers_nothing(self) -> None:
        assert voice_instrument_channels(Project.create(), "gone") == ()

    def test_the_instrument_asked_for_is_the_one_that_channel_names(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())
        project = _project(sample)
        channel = sample.reconstruction.playing_channels[0]

        exportable = voice_instrument(project, sample.id, channel)

        assert exportable is not None
        assert exportable.source.channel is channel

    def test_a_written_instrument_is_asked_for_by_naming_no_channel(self) -> None:
        voice = new_instrument("Lead")

        exportable = voice_instrument(_project(voice), voice.id, None)

        assert exportable is not None
        assert exportable.name == "Lead"

    def test_a_written_instrument_is_reached_by_naming_no_channel_alone(self) -> None:
        """It offers one instrument for every channel at once, so no channel names it by itself."""
        voice = new_instrument("Lead")

        assert voice_instrument(_project(voice), voice.id, ChannelName.NOISE) is None

    def test_a_voice_the_pool_lost_is_written_nowhere(self) -> None:
        assert voice_instrument(Project.create(), "gone", None) is None
