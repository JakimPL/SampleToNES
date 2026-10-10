import gc
from pathlib import Path
from typing import Final, List, Tuple

import numpy as np
import pytest

from sampletones_application.logic.shared import renders as renders_module
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from tests.conftest import RENDER_BUDGET
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, taking_turns_reconstruction

SOURCES: Final[Tuple[Path, Path]] = (Path("a.wav"), Path("b.wav"))
EDITED: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=11, duty_cycle=1)
EDITED_PITCH: Final[int] = 67


def _document() -> Reconstruction:
    return taking_turns_reconstruction(SOURCES).detached()


def _edited(document: Reconstruction) -> Reconstruction:
    return document.with_channel_data(
        SHARED_CHANNEL,
        [EDITED, EDITED],
        EDITED_PITCH,
        (),
        heard=document.recorded_stem_ids,
    )


@pytest.fixture
def document() -> Reconstruction:
    return _document()


class TestReadingARender:
    """A render is read from the streams it sounds and kept for the next read."""

    def test_the_render_is_what_the_document_sounds(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        channels = renders.channels(document)

        expected = rendered_channels(document)
        assert channels.keys() == expected.keys()
        assert all(np.array_equal(channels[name], expected[name]) for name in expected)
        assert np.array_equal(renders.mix(document), rendered_mix(document))

    def test_a_second_read_answers_with_the_kept_render(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        first = renders.channels(document)
        mixed = renders.mix(document)

        assert renders.channels(document) == first
        assert renders.mix(document) is mixed

    def test_a_stream_two_documents_share_renders_once(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        before = renders.channels(document)

        after = renders.channels(_edited(document))

        assert after[SOLE_CHANNEL] is before[SOLE_CHANNEL]
        assert after[SHARED_CHANNEL] is not before[SHARED_CHANNEL]

    def test_equal_streams_of_two_documents_render_apart(self, renders: RenderCache) -> None:
        first = renders.channels(_document())
        second = renders.channels(_document())

        assert second[SOLE_CHANNEL] is not first[SOLE_CHANNEL]
        assert np.array_equal(second[SOLE_CHANNEL], first[SOLE_CHANNEL])


class TestTheBudget:
    """The cache keeps audio within its budget, letting the renders read longest ago go first."""

    def test_the_oldest_render_goes_first(self, document: Reconstruction) -> None:
        sole = rendered_channels(document)[SOLE_CHANNEL].nbytes
        renders = RenderCache(budget_bytes=sole)
        kept = renders.channels(document)

        renders.channels(_edited(document))

        assert renders.held_bytes <= sole
        assert renders.channels(document)[SHARED_CHANNEL] is not kept[SHARED_CHANNEL]

    def test_a_render_read_again_stays(self, document: Reconstruction) -> None:
        renders = RenderCache(budget_bytes=RENDER_BUDGET)
        kept = renders.channels(document)

        renders.channels(_edited(document))

        assert renders.channels(document) == kept


class TestARenderGoesWithItsStream:
    """A render leaves the cache with the last document holding the stream it was made from."""

    def test_a_collected_document_releases_its_renders(self, renders: RenderCache) -> None:
        document = _document()
        renders.mix(document)
        assert renders.held_bytes > 0

        del document
        gc.collect()

        assert renders.held_bytes == 0


def _never_rendering(
    instructions: List[InstructionUnion],
    channel_name: ChannelName,
    config: Config,
) -> np.ndarray:
    raise AssertionError(f"{channel_name} was rendered")


class TestAdoptingRendersMadeElsewhere:
    """Renders a rebuild made on its worker are kept as the document's own and read back without rendering.

    ``held`` says what the cache holds for a document's channels without rendering, which is what
    a rebuild takes with it. A render already kept stays when the same stream's render is adopted
    again, and every kept render is read-only, since the readers it is shared with copy what they
    change.
    """

    def test_held_names_the_channels_read_so_far(self, renders: RenderCache, document: Reconstruction) -> None:
        assert renders.held(document) == {}

        kept = renders.channels(document)

        held = renders.held(document)
        assert held.keys() == kept.keys()
        assert all(held[name] is kept[name] for name in kept)

    def test_adopted_renders_answer_every_read(
        self,
        renders: RenderCache,
        document: Reconstruction,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        channels = rendered_channels(document)
        mixed = rendered_mix(document)

        renders.adopt(document, channels, mixed)

        monkeypatch.setattr(renders_module, "render_instructions", _never_rendering)
        assert all(renders.channels(document)[name] is channels[name] for name in channels)
        assert renders.mix(document) is mixed

    def test_a_kept_render_is_read_only(self, renders: RenderCache, document: Reconstruction) -> None:
        assert all(not rendered.flags.writeable for rendered in renders.channels(document).values())
        assert not renders.mix(document).flags.writeable

    def test_a_render_already_kept_stays_when_adopted_again(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        first = renders.channels(document)

        renders.adopt(document, rendered_channels(document), rendered_mix(document))

        after = renders.channels(document)
        assert all(after[name] is first[name] for name in first)
