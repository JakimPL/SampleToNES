import gc
from pathlib import Path
from typing import Final, FrozenSet, Tuple

import numpy as np
import pytest

from sampletones_application.logic.shared import renders as renders_module
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_core.audio.mixing import align, mix
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing, heard_renders
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from tests.conftest import RENDER_BUDGET
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, STEM_A_ID, STEM_B_ID, taking_turns_reconstruction

SOURCES: Final[Tuple[Path, Path]] = (Path("a.wav"), Path("b.wav"))
EDITED: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=11, duty_cycle=1)
EDITED_PITCH: Final[int] = 67
LONGER_FRAMES: Final[int] = 4
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


def _adopted(renders: RenderCache, document: Reconstruction) -> Tuple[dict, np.ndarray]:  # type: ignore[type-arg]
    """Keeps the document's renders the way a landing does, and hands back what was kept."""
    channels = rendered_channels(document)
    mixed = rendered_mix(document)
    renders.adopt(document, channels, mixed)
    return channels, mixed


def _whole_bytes(document: Reconstruction) -> int:
    """The bytes a document's channel renders and its mix take together."""
    return sum(rendered.nbytes for rendered in rendered_channels(document).values()) + rendered_mix(document).nbytes


def _room_for_one_more(document: Reconstruction) -> int:
    """A budget holding the document whole and one more render of its edited channel, so the next one evicts."""
    return _whole_bytes(document) + rendered_channels(document)[SHARED_CHANNEL].nbytes


@pytest.fixture
def document() -> Reconstruction:
    return _document()


class TestTheRendersALandingAdopts:
    """Renders a worker made are kept as the document's own and read back by identity, each stream's once."""

    def test_adopted_renders_are_read_back_by_identity(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        channels, mixed = _adopted(renders, document)

        held = renders.held(document)
        assert held.keys() == channels.keys()
        assert all(held[name] is channels[name] for name in channels)
        reading = renders.reading(document, _hearing(document.recorded_stem_ids))
        assert reading is not None
        assert reading.mix is mixed

    def test_a_stream_two_documents_share_is_kept_once(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        channels, _ = _adopted(renders, document)

        held = renders.held(_edited(document))

        assert held.keys() == {SOLE_CHANNEL}
        assert held[SOLE_CHANNEL] is channels[SOLE_CHANNEL]

    def test_equal_streams_of_two_documents_are_kept_apart(self, renders: RenderCache) -> None:
        first_document = _document()
        second_document = _document()
        first, _ = _adopted(renders, first_document)
        second, _ = _adopted(renders, second_document)

        assert renders.held(first_document)[SOLE_CHANNEL] is first[SOLE_CHANNEL]
        assert renders.held(second_document)[SOLE_CHANNEL] is second[SOLE_CHANNEL]
        assert second[SOLE_CHANNEL] is not first[SOLE_CHANNEL]
        assert np.array_equal(second[SOLE_CHANNEL], first[SOLE_CHANNEL])

    def test_the_cache_names_no_renderer(self) -> None:
        """Every render the cache keeps is a worker's result, so the module reaches no renderer."""
        assert not hasattr(renders_module, "render_instructions")


class TestTheBudget:
    """The cache keeps audio within its budget, letting the renders read longest ago go first.

    A document is adopted channel by channel in channel order and its mix last, so with no read
    between, the first channel's render is the oldest and goes first.
    """

    def test_the_oldest_render_goes_first(self, document: Reconstruction) -> None:
        renders = RenderCache(budget_bytes=_room_for_one_more(document))
        _adopted(renders, document)
        edited = _edited(document)

        shared, _ = _adopted(renders, edited)

        assert renders.held_bytes <= _room_for_one_more(document)
        assert renders.held(document).keys() == {SOLE_CHANNEL}
        held = renders.held(edited)
        assert held.keys() == {SOLE_CHANNEL, SHARED_CHANNEL}
        assert held[SHARED_CHANNEL] is shared[SHARED_CHANNEL]

    def test_a_render_read_again_stays(self, document: Reconstruction) -> None:
        renders = RenderCache(budget_bytes=_room_for_one_more(document))
        channels, _ = _adopted(renders, document)
        renders.held(document)

        _adopted(renders, _edited(document))

        held = renders.held(document)
        assert held.keys() == channels.keys()
        assert all(held[name] is channels[name] for name in channels)

    def test_a_landing_is_kept_whole_within_a_budget_below_it(self, document: Reconstruction) -> None:
        """A document larger than the budget is kept whole as it lands, and the previous renders go."""
        renders = RenderCache(budget_bytes=_whole_bytes(document) - 1)
        _adopted(renders, _document())
        channels, mixed = _adopted(renders, document)

        held = renders.held(document)
        assert held.keys() == channels.keys()
        assert all(held[name] is channels[name] for name in channels)
        reading = renders.reading(document, _hearing(document.recorded_stem_ids))
        assert reading is not None
        assert reading.mix is mixed

    def test_the_next_landing_evicts_a_document_larger_than_the_budget(self, document: Reconstruction) -> None:
        renders = RenderCache(budget_bytes=_whole_bytes(document) - 1)
        _adopted(renders, document)

        _adopted(renders, _document())

        assert renders.held(document) == {}
        assert renders.held_bytes <= _whole_bytes(document)

    def test_a_budget_leaves_room_for_what_fits(self, document: Reconstruction) -> None:
        renders = RenderCache(budget_bytes=RENDER_BUDGET)
        channels, _ = _adopted(renders, document)

        _adopted(renders, _edited(document))

        held = renders.held(document)
        assert all(held[name] is channels[name] for name in channels)


class TestARenderGoesWithItsStream:
    """A render leaves the cache with the last document holding the stream it was made from."""

    def test_a_collected_document_releases_its_renders(self, renders: RenderCache) -> None:
        document = _document()
        _adopted(renders, document)
        assert renders.held_bytes > 0

        del document
        gc.collect()

        assert renders.held_bytes == 0


class TestTheOriginalOfTheRecordingsHeard:
    """The mix of the recordings heard is kept under the recordings it was mixed from, in record order, so every
    document holding those recordings reads one mix, and the mix goes with the recordings.
    """

    @staticmethod
    def _recordings() -> Tuple[np.ndarray, np.ndarray]:
        return np.ones(8, dtype=np.float32), np.full(8, 0.5, dtype=np.float32)

    def test_it_is_read_back_by_the_recordings_in_order(self, renders: RenderCache, document: Reconstruction) -> None:
        first, second = self._recordings()
        mixed = mix([first, second])

        renders.adopt_original((first, second), document.config, mixed)

        assert renders.original((first, second), document.config) is mixed
        assert renders.original((first,), document.config) is None
        assert renders.original((second, first), document.config) is None

    def test_two_documents_holding_the_recordings_read_one_mix(
        self, renders: RenderCache, document: Reconstruction
    ) -> None:
        first, second = self._recordings()
        mixed = mix([first, second])
        other = document.model_copy()
        renders.adopt_original((first, second), document.config, mixed)

        assert renders.original((first, second), other.config) is mixed

    def test_the_kept_mix_is_read_only(self, renders: RenderCache, document: Reconstruction) -> None:
        first, second = self._recordings()
        renders.adopt_original((first, second), document.config, mix([first, second]))

        kept = renders.original((first, second), document.config)

        assert kept is not None
        assert not kept.flags.writeable

    def test_a_recording_let_go_of_takes_the_mix_with_it(self, renders: RenderCache, document: Reconstruction) -> None:
        first, second = self._recordings()
        renders.adopt_original((first, second), document.config, mix([first, second]))
        assert renders.held_bytes > 0

        del first
        gc.collect()

        assert renders.held_bytes == 0
        assert renders.original((second,), document.config) is None


class TestAdoptingRendersMadeElsewhere:
    """``held`` says what the cache holds for a document's channels, which is what a rebuild takes with it.

    A render already kept stays when the same stream's render is adopted again, and every kept
    render is read-only, since the readers it is shared with copy what they change.
    """

    def test_held_names_the_channels_kept_so_far(self, renders: RenderCache, document: Reconstruction) -> None:
        assert renders.held(document) == {}

        channels, _ = _adopted(renders, document)

        held = renders.held(document)
        assert held.keys() == channels.keys()
        assert all(held[name] is channels[name] for name in channels)

    def test_a_kept_render_is_read_only(self, renders: RenderCache, document: Reconstruction) -> None:
        _, mixed = _adopted(renders, document)

        assert all(not rendered.flags.writeable for rendered in renders.held(document).values())
        assert not mixed.flags.writeable

    def test_a_render_already_kept_stays_when_adopted_again(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        first, _ = _adopted(renders, document)

        _adopted(renders, document)

        after = renders.held(document)
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
        _, mixed = _adopted(renders, document)

        reading = renders.reading(document, _hearing(document.recorded_stem_ids))

        assert reading is not None
        assert reading.mix is mixed
        assert reading.playing is mixed

    def test_a_recording_left_out_reads_nothing_until_its_sound_is_kept(
        self,
        renders: RenderCache,
        document: Reconstruction,
    ) -> None:
        _adopted(renders, document)
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
        _, mixed = _adopted(renders, document)
        hearing = _hearing(document.recorded_stem_ids, frozenset({SOLE_CHANNEL}))

        assert renders.reading(document, hearing) is None

        renders.adopt_heard(document, hearing, _heard(document, hearing))

        reading = renders.reading(document, hearing)
        assert reading is not None
        assert reading.mix is mixed
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
        _, mixed = _adopted(renders, document)
        beyond = _hearing(document.recorded_stem_ids | frozenset({STEM_B_ID + 10}))

        reading = renders.reading(document, beyond)

        assert reading is not None
        assert reading.mix is mixed

    def test_no_channel_on_reads_silence_of_the_documents_own_length(self, renders: RenderCache) -> None:
        """Two documents at equal settings, every channel off, each read a silence as long as their own mix."""
        shorter = _document()
        longer = _document().with_channel_data(
            SHARED_CHANNEL,
            [EDITED] * LONGER_FRAMES,
            EDITED_PITCH,
            (),
            heard=shorter.recorded_stem_ids,
        )
        assert len(rendered_mix(longer)) > len(rendered_mix(shorter))
        nothing_on = _hearing(shorter.recorded_stem_ids, frozenset())
        for document in (shorter, longer):
            _adopted(renders, document)
            renders.adopt_heard(document, nothing_on, _heard(document, nothing_on))

        readings = [renders.reading(document, nothing_on) for document in (shorter, longer)]

        assert all(reading is not None for reading in readings)
        assert [len(reading.playing) for reading in readings if reading is not None] == [
            len(rendered_mix(shorter)),
            len(rendered_mix(longer)),
        ]
        assert all(not reading.playing.any() for reading in readings if reading is not None)

    def test_silence_is_kept_nowhere(self, renders: RenderCache, document: Reconstruction) -> None:
        nothing_on = _hearing(document.recorded_stem_ids, frozenset())
        _adopted(renders, document)
        before = renders.held_bytes

        renders.adopt_heard(document, nothing_on, _heard(document, nothing_on))

        assert renders.held_bytes == before

    def test_a_heard_mix_goes_with_the_record_it_was_keyed_by(self, renders: RenderCache) -> None:
        document = _document()
        hearing = _hearing(frozenset({STEM_A_ID}))
        _adopted(renders, document)
        renders.adopt_heard(document, hearing, _heard(document, hearing))
        before = renders.held_bytes

        del document
        gc.collect()

        assert renders.held_bytes < before
        assert renders.held_bytes == 0
