import gc
from pathlib import Path
from typing import Final, FrozenSet, List, Tuple

import numpy as np
import pytest

from sampletones_application.logic.shared import renders as renders_module
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_core.audio.mixing import align
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing, heard_renders
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from tests.conftest import RENDER_BUDGET
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, STEM_A_ID, STEM_B_ID, taking_turns_reconstruction

SOURCES: Final[Tuple[Path, Path]] = (Path("a.wav"), Path("b.wav"))
EDITED: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=11, duty_cycle=1)
EDITED_PITCH: Final[int] = 67
EVERY_CHANNEL: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())


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


def _hearing(stem_ids: FrozenSet[int], channels_on: FrozenSet[ChannelName] = EVERY_CHANNEL) -> Hearing:
    return Hearing(selection=StemSelection.everywhere(stem_ids, ChannelName.items()), channels_on=channels_on)


def _heard(document: Reconstruction, hearing: Hearing):  # type: ignore[no-untyped-def]
    return heard_renders(document, hearing, rendered_channels(document), rendered_mix(document))


class TestReadingAHearing:
    """A hearing's reading is a lookup alone: the heard mix and what plays, or nothing where either is missing.

    A hearing leaving nothing out and keeping every channel on reads the document's own mix, so the
    renders a landing adopts answer it. One leaving a recording out reads a mix keyed by the owners
    heard on each channel, which the worker renders and the landing adopts under the same key.
    """

    def test_a_document_heard_whole_reads_its_own_mix(self, renders: RenderCache, document: Reconstruction) -> None:
        renders.adopt(document, rendered_channels(document), rendered_mix(document))

        reading = renders.reading(document, _hearing(document.recorded_stem_ids))

        assert reading is not None
        assert reading.mix is renders.mix(document)
        assert reading.playing is renders.mix(document)

    def test_a_recording_left_out_reads_nothing_until_its_sound_is_kept(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        renders.adopt(document, rendered_channels(document), rendered_mix(document))
        hearing = _hearing(frozenset({STEM_A_ID}))

        assert renders.reading(document, hearing) is None

        renders.adopt_heard(document, hearing, _heard(document, hearing))

        reading = renders.reading(document, hearing)
        assert reading is not None
        np.testing.assert_array_equal(reading.mix, _heard(document, hearing).mix)

    def test_a_narrower_channel_choice_reads_nothing_until_its_sound_is_kept(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        renders.adopt(document, rendered_channels(document), rendered_mix(document))
        hearing = _hearing(document.recorded_stem_ids, frozenset({SOLE_CHANNEL}))

        assert renders.reading(document, hearing) is None

        renders.adopt_heard(document, hearing, _heard(document, hearing))

        reading = renders.reading(document, hearing)
        assert reading is not None
        assert reading.mix is renders.mix(document)
        np.testing.assert_array_equal(
            reading.playing,
            align([rendered_channels(document)[SOLE_CHANNEL]], len(reading.mix))[0],
        )

    def test_recordings_heard_beyond_a_channel_read_as_the_channel_heard_whole(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        """A heard set is keyed by the owners it reaches, so a stem absent from a channel changes its key nowhere."""
        renders.adopt(document, rendered_channels(document), rendered_mix(document))
        beyond = _hearing(document.recorded_stem_ids | frozenset({STEM_B_ID + 10}))

        reading = renders.reading(document, beyond)

        assert reading is not None
        assert reading.mix is renders.mix(document)

    def test_a_heard_mix_goes_with_the_record_it_was_keyed_by(self, renders: RenderCache) -> None:
        document = _document()
        hearing = _hearing(frozenset({STEM_A_ID}))
        renders.adopt(document, rendered_channels(document), rendered_mix(document))
        renders.adopt_heard(document, hearing, _heard(document, hearing))
        before = renders.held_bytes

        del document
        gc.collect()

        assert renders.held_bytes < before
        assert renders.held_bytes == 0
