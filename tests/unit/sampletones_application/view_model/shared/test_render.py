from pathlib import Path
from typing import Final

from sampletones_application.view_model.shared.render import (
    RenderPhase,
    SongRenderSettings,
    SongRenderViewModel,
)
from sampletones_core.audio.writers import (
    AudioDepth,
    AudioFormat,
    Mp3OutputSpec,
    WaveOutputSpec,
)

DESTINATION: Final[Path] = Path("/home/user/song.wav")
TOTAL_SAMPLES: Final[int] = 44100


def wave_settings(
    *,
    sample_rate: int = 44100,
    depth: AudioDepth = AudioDepth.PCM_16,
) -> SongRenderSettings:
    return SongRenderSettings(
        spec=WaveOutputSpec(sample_rate=sample_rate, depth=depth),
        normalize=False,
    )


def view_model(
    settings: SongRenderSettings,
    *,
    phase: RenderPhase = RenderPhase.CONFIGURING,
    total_samples: int = TOTAL_SAMPLES,
) -> SongRenderViewModel:
    return SongRenderViewModel(
        phase=phase,
        formats=(AudioFormat.WAVE, AudioFormat.MP3),
        depths=(AudioDepth.PCM_16, AudioDepth.PCM_24),
        settings=settings,
        destination=DESTINATION,
        total_samples=total_samples,
        status_text="",
        progress=0.0,
    )


class TestChoicesFollowTheFormat:
    """Every choice a dialog stands at is reconciled against what the container accepts."""

    def test_a_rate_the_new_format_encodes_is_kept(self) -> None:
        settings = wave_settings(sample_rate=48000).with_format(AudioFormat.MP3)

        assert settings.spec.audio_format == AudioFormat.MP3
        assert settings.spec.sample_rate == 48000

    def test_a_rate_the_new_format_leaves_behind_moves_to_the_nearest(self) -> None:
        settings = wave_settings(sample_rate=192000).with_format(AudioFormat.MP3)

        assert settings.spec.sample_rate == 48000

    def test_a_container_storing_samples_opens_on_a_depth(self) -> None:
        settings = SongRenderSettings.initial(AudioFormat.MP3).with_format(AudioFormat.WAVE)

        assert settings.depth is not None
        assert settings.bitrate is None

    def test_a_depth_survives_a_rate_change(self) -> None:
        settings = wave_settings(depth=AudioDepth.PCM_U8).with_sample_rate(8000)

        assert settings.spec.sample_rate == 8000
        assert settings.depth == AudioDepth.PCM_U8

    def test_the_normalise_choice_stands_through_a_format_change(self) -> None:
        settings = wave_settings().with_normalize(True).with_format(AudioFormat.MP3)

        assert settings.normalize


class TestBitratesFollowTheRate:
    """Each MPEG version defines its own ladder, so the bitrate follows the rate that selects it."""

    def test_a_bitrate_the_new_rate_reaches_is_kept(self) -> None:
        settings = SongRenderSettings(
            spec=Mp3OutputSpec(sample_rate=44100, bitrate=64),
            normalize=False,
        ).with_sample_rate(22050)

        assert settings.bitrate == 64

    def test_a_bitrate_beyond_the_new_ladder_moves_onto_it(self) -> None:
        settings = SongRenderSettings(
            spec=Mp3OutputSpec(sample_rate=44100, bitrate=320),
            normalize=False,
        ).with_sample_rate(8000)

        assert settings.bitrate == 64

    def test_the_chosen_bitrate_is_taken(self) -> None:
        settings = SongRenderSettings.initial(AudioFormat.MP3).with_bitrate(96)

        assert settings.bitrate == 96


class TestWhatTheDialogDraws:
    def test_a_container_storing_samples_offers_depths_and_no_bitrates(self) -> None:
        view = view_model(wave_settings())

        assert view.stores_samples
        assert view.bitrates == ()

    def test_a_container_encoding_to_a_bitrate_offers_the_ladder_of_its_rate(self) -> None:
        view = view_model(SongRenderSettings.initial(AudioFormat.MP3).with_sample_rate(8000))

        assert not view.stores_samples
        assert view.bitrates == (64, 56, 48, 40, 32, 24, 16, 8)

    def test_the_offered_rates_are_the_containers_own(self) -> None:
        view = view_model(SongRenderSettings.initial(AudioFormat.MP3))

        assert view.sample_rates == (8000, 16000, 22050, 44100, 48000)

    def test_the_projected_duration_is_the_song_at_the_chosen_rate(self) -> None:
        view = view_model(wave_settings(sample_rate=44100), total_samples=88200)

        assert view.duration_seconds == 2.0

    def test_setting_up_shows_the_setup_alone(self) -> None:
        view = view_model(wave_settings(), phase=RenderPhase.CONFIGURING)

        assert view.setup_visible
        assert not view.progress_visible
        assert view.render_enabled
        assert view.is_active

    def test_rendering_shows_the_progress_alone(self) -> None:
        view = view_model(wave_settings(), phase=RenderPhase.RENDERING)

        assert view.progress_visible
        assert not view.setup_visible
        assert not view.render_enabled
        assert view.cancel_enabled

    def test_a_render_already_stopping_takes_no_further_stop(self) -> None:
        view = view_model(wave_settings(), phase=RenderPhase.CANCELLING)

        assert view.is_active
        assert not view.cancel_enabled

    def test_a_song_holding_no_rows_starts_no_render(self) -> None:
        view = view_model(wave_settings(), total_samples=0)

        assert not view.render_enabled

    def test_an_outcome_releases_the_application(self) -> None:
        for phase in (RenderPhase.COMPLETED, RenderPhase.CANCELLED, RenderPhase.FAILED):
            assert not view_model(wave_settings(), phase=phase).is_active
