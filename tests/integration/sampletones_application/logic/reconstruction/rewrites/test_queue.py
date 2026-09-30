import time
from pathlib import Path
from typing import Final, Iterator, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.coordinators.tabs.reconstruction import ReconstructionTabCoordinator
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.rewrites.queue import ReconstructionRewrites
from sampletones_application.logic.reconstruction.rewrites.steps import (
    ChannelChange,
    RateChange,
    StemRemovalRequest,
)
from sampletones_application.services.regeneration.service import RegenerationService
from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.reconstructions import Reconstruction
from tests.suite.application import draw_frame, live_queue, scheduling
from tests.suite.stems import (
    SHARED_CHANNEL,
    SHARED_OWNERS,
    SOLE_CHANNEL,
    STEM_A_ID,
    STEM_B_ID,
    TAKING_TURNS_PITCH,
    taking_turns_file,
)

__all__ = ["live_queue", "scheduling", "taking_turns_file"]

DRAG: Final[Tuple[Tuple[int, int], ...]] = ((1, 1), (2, 2), (3, 3), (4, 4), (6, 6))
ARPEGGIO: Final[Tuple[int, int]] = (4, 3)
RETUNED_FREQUENCY: Final[int] = 50
SETTLE_SECONDS: Final[float] = 10.0
POLL_SECONDS: Final[float] = 0.005


@pytest.fixture
def coordinator(
    live_queue: None,
    scheduling: SchedulingBehavior,
    taking_turns_file: Path,
) -> Iterator[ReconstructionCoordinator]:
    """The coordinator over the two-recording document opened from its file, rebuilt on the real worker."""
    manager = ReconstructionManager(scheduling=scheduling)
    coordinator = ReconstructionCoordinator(
        manager,
        MagicMock(),
        ReconstructionRewrites(manager, RegenerationService()),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
        on_reconstruction_updated=MagicMock(),
    )
    coordinator.set_reconstructions_tab(MagicMock(spec=ReconstructionTabCoordinator))
    manager.load_reconstruction(taking_turns_file)
    yield coordinator


def _settle(coordinator: ReconstructionCoordinator) -> None:
    """Draws frames until every step has landed, the way the render loop drains the results."""
    deadline = time.monotonic() + SETTLE_SECONDS
    while coordinator._rewrites.is_busy:
        assert time.monotonic() < deadline, "the steps never settled"
        draw_frame()
        time.sleep(POLL_SECONDS)


def _open_document(coordinator: ReconstructionCoordinator) -> Reconstruction:
    reconstruction = coordinator._reconstruction_manager.reconstruction
    assert reconstruction is not None
    return reconstruction


class TestEditingAFileBackedDocumentAtSpeed:
    """A drag, an arpeggio, a removal and a rate change made faster than the worker rebuilds all land, in order."""

    @pytest.fixture
    def settled(self, coordinator: ReconstructionCoordinator) -> ReconstructionCoordinator:
        for volume in DRAG:
            coordinator.request_rewrite(
                ChannelChange(
                    channel_name=SHARED_CHANNEL,
                    feature_key=FeatureKey.VOLUME,
                    envelopes={FeatureKey.VOLUME: Envelope[int](items=volume)},
                    initial_pitch=None,
                )
            )
        coordinator.request_rewrite(
            ChannelChange(
                channel_name=SHARED_CHANNEL,
                feature_key=FeatureKey.ARPEGGIO,
                envelopes={FeatureKey.ARPEGGIO: Envelope[int](items=ARPEGGIO)},
                initial_pitch=None,
            )
        )
        coordinator.request_rewrite(StemRemovalRequest(stem_id=STEM_B_ID, stem_name="b"))
        coordinator.request_rewrite(RateChange(nes_frequency=RETUNED_FREQUENCY))
        _settle(coordinator)
        return coordinator

    def test_the_drag_lands_where_it_ended(self, settled: ReconstructionCoordinator) -> None:
        kept = _open_document(settled).instructions[SHARED_CHANNEL][SHARED_OWNERS.index(STEM_A_ID)]

        assert kept.volume == DRAG[-1][0]

    def test_the_arpeggio_lands_beside_it(self, settled: ReconstructionCoordinator) -> None:
        kept = _open_document(settled).instructions[SHARED_CHANNEL][SHARED_OWNERS.index(STEM_A_ID)]

        assert kept.pitch == TAKING_TURNS_PITCH + ARPEGGIO[0]

    def test_the_recording_taken_out_stays_out(self, settled: ReconstructionCoordinator) -> None:
        reconstruction = _open_document(settled)

        assert list(reconstruction.stems_data.config.entries_by_id) == [STEM_A_ID]
        assert SOLE_CHANNEL not in reconstruction.playing_channels

    def test_the_recording_that_stays_keeps_its_audio(self, settled: ReconstructionCoordinator) -> None:
        data = settled._reconstruction_manager.current_reconstruction

        assert data is not None
        assert len(data.stem_audios) == 1

    def test_the_document_runs_at_the_new_rate(self, settled: ReconstructionCoordinator) -> None:
        assert _open_document(settled).config.nes_frequency == RETUNED_FREQUENCY

    def test_the_waveform_fades_for_the_whole_span(self, settled: ReconstructionCoordinator) -> None:
        dims = [entry.args[0] for entry in settled._tab.set_reconstruction_dimmed.call_args_list]

        assert dims == [True, False]
