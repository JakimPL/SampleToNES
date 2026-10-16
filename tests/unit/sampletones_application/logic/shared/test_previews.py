from typing import Final, Iterator, List, Tuple

import numpy as np
import pytest

from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.services.regeneration.jobs import ListeningJob
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_mix
from sampletones_core.reconstructions.reconstruction.stems.hearing import whole_hearing
from tests.suite.regeneration import HeldRegeneration
from tests.suite.renders import warmed
from tests.suite.sequencer import sample_reconstruction

PREVIEWED_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]


@pytest.fixture
def regeneration() -> HeldRegeneration:
    return HeldRegeneration()


@pytest.fixture
def previews(renders: RenderCache, regeneration: HeldRegeneration) -> DocumentPreviews:
    return DocumentPreviews(renders, regeneration)


class Played:
    """Every sound a preview played, with the rate it played at."""

    def __init__(self) -> None:
        self.sounds: List[Tuple[np.ndarray, int]] = []

    def __call__(self, audio: np.ndarray, sample_rate: int) -> None:
        self.sounds.append((audio, sample_rate))


@pytest.fixture
def played() -> Played:
    return Played()


def _document() -> Reconstruction:
    return sample_reconstruction(PREVIEWED_CHANNELS)


def _unexpected(exception: Exception) -> None:
    raise AssertionError(f"a preview's render failed: {exception}")


def _sounded(played: Played, document: Reconstruction) -> bool:
    """Whether exactly the whole document was played, once, at the rate it was made at."""
    if len(played.sounds) != 1:
        return False

    audio, sample_rate = played.sounds[0]
    return bool(np.array_equal(audio, rendered_mix(document))) and sample_rate == document.config.sample_rate


class TestAPreviewOfAKeptDocument:
    def test_it_plays_at_once(
        self,
        previews: DocumentPreviews,
        renders: RenderCache,
        regeneration: HeldRegeneration,
        played: Played,
    ) -> None:
        document = _document()
        warmed(renders, document, whole_hearing(document), {})

        previews.play(document, played, _unexpected)

        assert _sounded(played, document)
        assert regeneration.held == ()
        assert not previews.is_busy


class TestAPreviewOfAnUnkeptDocument:
    """The sound is asked of the worker once, played when it lands, and kept for the next ask."""

    def test_it_asks_once_and_plays_at_the_landing(
        self,
        previews: DocumentPreviews,
        renders: RenderCache,
        regeneration: HeldRegeneration,
        played: Played,
    ) -> None:
        document = _document()

        previews.play(document, played, _unexpected)

        assert played.sounds == []
        assert previews.is_busy
        (job,) = regeneration.held
        assert isinstance(job, ListeningJob)
        assert job.reconstruction is document
        assert job.hearing == whole_hearing(document)
        assert job.kept == renders.held(document)
        regeneration.finish()
        assert _sounded(played, document)
        assert regeneration.held == ()
        assert renders.reading(document, whole_hearing(document)) is not None
        assert not previews.is_busy

    def test_a_newer_request_replaces_the_one_waiting(
        self,
        previews: DocumentPreviews,
        regeneration: HeldRegeneration,
        played: Played,
    ) -> None:
        first = _document()
        second = _document()
        previews.play(first, played, _unexpected)

        previews.play(second, played, _unexpected)
        regeneration.finish()

        assert played.sounds == []
        (job,) = regeneration.held
        assert job.reconstruction is second
        regeneration.finish()
        assert _sounded(played, second)

    def test_a_canceled_preview_lands_silently_and_fills_the_cache(
        self,
        previews: DocumentPreviews,
        renders: RenderCache,
        regeneration: HeldRegeneration,
        played: Played,
    ) -> None:
        document = _document()
        previews.play(document, played, _unexpected)

        previews.cancel()
        assert previews.is_busy
        regeneration.finish()

        assert played.sounds == []
        assert renders.reading(document, whole_hearing(document)) is not None
        assert not previews.is_busy

    def test_a_document_no_longer_wanted_is_kept_while_the_wanted_one_plays_from_the_cache(
        self,
        previews: DocumentPreviews,
        renders: RenderCache,
        regeneration: HeldRegeneration,
        played: Played,
    ) -> None:
        first = _document()
        second = _document()
        previews.play(first, played, _unexpected)
        warmed(renders, second, whole_hearing(second), {})
        previews.play(second, played, _unexpected)
        assert played.sounds == []

        regeneration.finish()

        assert _sounded(played, second)
        assert regeneration.held == ()
        assert renders.reading(first, whole_hearing(first)) is not None

    def test_a_failed_render_is_reported_and_the_next_wanted_document_starts(
        self,
        previews: DocumentPreviews,
        regeneration: HeldRegeneration,
        played: Played,
    ) -> None:
        first = _document()
        second = _document()
        failures: List[Exception] = []
        failure = RuntimeError("the worker fell over")
        previews.play(first, played, failures.append)
        previews.play(second, played, failures.append)

        regeneration.fail(failure)

        assert failures == [failure]
        assert played.sounds == []
        (job,) = regeneration.held
        assert job.reconstruction is second

    def test_a_failed_render_of_the_wanted_document_is_asked_again_by_a_new_gesture_alone(
        self,
        previews: DocumentPreviews,
        regeneration: HeldRegeneration,
        played: Played,
    ) -> None:
        document = _document()
        failures: List[Exception] = []
        previews.play(document, played, failures.append)

        regeneration.fail(RuntimeError("the worker fell over"))

        assert regeneration.held == ()
        assert not previews.is_busy
        previews.play(document, played, failures.append)
        assert len(regeneration.held) == 1

    def test_a_result_arriving_with_nothing_on_its_way_raises(self, previews: DocumentPreviews) -> None:
        """A second reader sharing the service instance would land its results here, which is refused."""
        document = _document()
        stray = HeldRegeneration()
        stray.subscribe(previews._on_result)
        stray.start_listening(document, hearing=whole_hearing(document), kept={}, recordings={})

        with pytest.raises(RuntimeError, match="no preview was on its way"):
            stray.finish()


class TestAShutdownMidPreview:
    """A shutdown asked for while a preview renders ends the job with nothing played and nothing kept."""

    @pytest.fixture(autouse=True)
    def armed_again(self) -> Iterator[None]:
        yield
        SingleThreadExecutor.reset_shutdown()

    def test_nothing_plays_and_nothing_is_kept(
        self,
        previews: DocumentPreviews,
        renders: RenderCache,
        regeneration: HeldRegeneration,
        played: Played,
    ) -> None:
        document = _document()
        previews.play(document, played, _unexpected)

        SingleThreadExecutor.request_shutdown()
        regeneration.finish()

        assert played.sounds == []
        assert renders.reading(document, whole_hearing(document)) is None
