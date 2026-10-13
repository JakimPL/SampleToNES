import time
from typing import Final, List

import numpy as np
import pytest

from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.services.regeneration.service import RegenerationService
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.renders import rendered_mix
from tests.conftest import RENDER_BUDGET
from tests.suite.application import draw_frame, live_queue
from tests.suite.sequencer import sample_reconstruction

__all__ = ["live_queue"]

PREVIEWED_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]
SETTLE_SECONDS: Final[float] = 10.0
POLL_SECONDS: Final[float] = 0.005


@pytest.fixture
def previews(live_queue: None) -> DocumentPreviews:
    """Previews over a cache of their own, rendered on the real worker and landed through the live queue."""
    return DocumentPreviews(RenderCache(budget_bytes=RENDER_BUDGET), RegenerationService())


def _settle(previews: DocumentPreviews) -> None:
    """Draws frames until the preview has landed, the way the render loop drains the results."""
    deadline = time.monotonic() + SETTLE_SECONDS
    while previews.is_busy:
        assert time.monotonic() < deadline, "the preview never landed"
        draw_frame()
        time.sleep(POLL_SECONDS)


def _unexpected(exception: Exception) -> None:
    raise AssertionError(f"a preview's render failed: {exception}")


class TestAPreviewOnTheRealWorker:
    def test_the_sound_lands_and_a_second_ask_answers_from_the_cache(self, previews: DocumentPreviews) -> None:
        document = sample_reconstruction(PREVIEWED_CHANNELS)
        played: List[np.ndarray] = []

        previews.play(document, played.append, _unexpected)
        _settle(previews)

        assert len(played) == 1
        np.testing.assert_array_equal(played[0], rendered_mix(document))
        previews.play(document, played.append, _unexpected)
        assert len(played) == 2
        assert played[1] is played[0]
