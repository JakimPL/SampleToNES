import time
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Callable, Dict, Final, FrozenSet, List, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.edit import ReconstructionEdit
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.reconstruction import (
    ReconstructionPanelLogic,
)
from sampletones_application.logic.reconstruction.rewrites.queue import (
    ReconstructionRewrites,
)
from sampletones_application.logic.reconstruction.rewrites.steps import ChannelChange
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.services.regeneration.service import RegenerationService
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.constants.general import BYTES_PER_MEGABYTE
from tests.suite.application import HeldQueue
from tests.suite.history.wiring import wired_history
from tests.suite.language import FakeLanguageManager
from tests.suite.long_documents import VOLUMES, long_document
from tests.suite.questions import dialogs_on_the_line

SHORT_SECONDS: Final[float] = 30.0
LONG_SECONDS: Final[float] = 120.0
EDITS: Final[int] = 5
HISTORY_BUDGET: Final[int] = 16
RENDER_BUDGET: Final[int] = 1024 * BYTES_PER_MEGABYTE
EDITED_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
MUTED_STEM_ID: Final[int] = 1
RECORDINGS: Final[int] = 2
RECORDING_FREQUENCY: Final[float] = 220.0
RECORDING_AMPLITUDE: Final[float] = 0.5
LOWEST_LEVEL: Final[int] = 1
NO_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset()
DOCUMENT_NAME: Final[str] = "Long conversion"


@dataclass(frozen=True)
class Landing:
    """What one edit cost: the worker's seconds up to its report, and the render thread's seconds landing it."""

    worker_seconds: float
    landing_seconds: float


def _timed(work: Callable[[], None]) -> float:
    started = time.perf_counter()
    work()
    return time.perf_counter() - started


def _discard(*readings: object, **named: object) -> None:
    """Where the panel's readings go: the tab would draw them, and the meter reads their cost alone."""


def _session_manager() -> MagicMock:
    session_manager = MagicMock()
    session_manager.get_instrument_path.return_value = Path("/tmp/instruments")
    session_manager.get_audio_path.return_value = Path("/tmp/audio")
    return session_manager


class LandingMeter:
    """The Reconstructions tab's edit path with no DearPyGui, wired the way the composition root wires it.

    The real regeneration runs on its worker, the rewrites take the steps, the coordinator lands each
    edit through a strict history over a project, and the panel logic answers every reading the tab
    would draw. The queue the render loop drains is held, so what a landing costs the render thread
    is read by draining it.
    """

    def __init__(self, scheduling: SchedulingBehavior) -> None:
        self.renders = RenderCache(budget_bytes=RENDER_BUDGET)
        self.manager = ReconstructionManager(scheduling=scheduling, renders=self.renders)
        self.rewrites = ReconstructionRewrites(self.manager, RegenerationService())
        self.controller = ProjectController(ProjectManager())
        self.history = wired_history(self.controller, budget=HISTORY_BUDGET, strict=True)
        export_backends: Dict[ExportFormat, ExportBackend] = {}
        self.panel = ReconstructionPanelLogic(_session_manager(), self.manager, MagicMock(), export_backends)
        self.panel.on_view_changed = _discard
        self.panel.on_audio_data_changed = _discard
        self.panel.on_waveform_load_changed = _discard
        self.panel.on_waveform_update_changed = _discard
        self.panel.on_waveform_cleared = _discard
        self.panel.on_waveform_source_changed = _discard
        self.panel.on_stems_view_changed = _discard
        self.panel.on_ownership_changed = _discard
        self.panel.on_heard_changed = _discard
        self.coordinator = ReconstructionCoordinator(
            self.manager,
            MagicMock(),
            self.rewrites,
            MagicMock(),
            self.controller,
            self.history,
            dialogs=dialogs_on_the_line(),
            language_manager=FakeLanguageManager({}),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
            on_reconstruction_updated=self._write_back,
        )
        self.coordinator.set_reconstructions_tab(self._tab())
        self.controller.on_project_replaced = self.history.reset
        self.controller.new()

    def open_as_sample(self, document: Reconstruction) -> float:
        """Adds ``document`` to the project and opens it on the tab, which renders every channel cold.

        Returns:
            float: The seconds the opening took.
        """
        with self.history.transaction(HistoryAction.ADD_SAMPLE):
            sample = self.controller.add_sample(document, DOCUMENT_NAME)

        return _timed(
            lambda: self.manager.load_reconstruction_object(
                sample.reconstruction,
                name=DOCUMENT_NAME,
                voice_id=sample.id,
            )
        )

    def open_standalone(self, document: Reconstruction) -> float:
        """Opens ``document`` on the tab as a file would be, its recordings read, which renders every channel cold.

        Returns:
            float: The seconds the opening took.
        """
        return _timed(
            lambda: self.manager.load_reconstruction_object(
                document,
                name=DOCUMENT_NAME,
                voice_id=None,
            )
        )

    def mute(self, stem_id: int) -> None:
        """Leaves one recording out of what the reader hears, the way a box on the stems card does."""
        self.panel.set_stem_channels(stem_id, NO_CHANNELS)

    def edit(self, step: int) -> Landing:
        """Moves the edited channel's volume by ``step`` and lands the rebuild, reading what each side cost."""
        envelopes = self.manager.current_features
        assert envelopes is not None
        volume = envelopes[EDITED_CHANNEL].volume
        moved = volume.model_copy(
            update={"items": tuple(LOWEST_LEVEL + (item + step) % (VOLUMES - 1) for item in volume.items)}
        )
        change = ChannelChange(
            channel_name=EDITED_CHANNEL,
            feature_key=FeatureKey.VOLUME,
            envelopes={FeatureKey.VOLUME: moved},
            initial_pitch=None,
        )
        queue = HeldQueue()
        with patch.object(CallbackQueue, "add", queue.add):
            self.rewrites.request(change)
            worker_seconds = _timed(SingleThreadExecutor.join_all)
            landing_seconds = _timed(queue.drain)

        return Landing(worker_seconds=worker_seconds, landing_seconds=landing_seconds)

    def _tab(self) -> MagicMock:
        tab = MagicMock(spec=ReconstructionTabCoordinator)
        tab.display_reconstruction.side_effect = self.panel.display_reconstruction
        tab.update_reconstruction.side_effect = self.panel.update_reconstruction
        tab.redraw_reconstruction.side_effect = self.panel.update_reconstruction
        return tab

    def _write_back(self, edit: ReconstructionEdit) -> None:
        voice_id = self.manager.voice_id
        if voice_id is None:
            return

        with self.history.transaction(edit.history_action, coalesce=edit.coalesce_key(voice_id)):
            self.controller.replace_sample_reconstruction(voice_id, edit.reconstruction)


def _report(
    label: str,
    opening: float,
    landings: List[Landing],
    cache_bytes: int,
) -> None:
    workers = [landing.worker_seconds for landing in landings]
    landed = [landing.landing_seconds for landing in landings]
    print(
        f"\n{label}\n"
        f"  opening, every channel rendered cold: {opening:.3f} s\n"
        f"  per edit, median of {len(landings)} (least): worker {median(workers):.3f} s ({min(workers):.3f} s), "
        f"landing on the render thread {median(landed):.3f} s ({min(landed):.3f} s)\n"
        f"  renders kept: {cache_bytes / BYTES_PER_MEGABYTE:.0f} MB"
    )


@pytest.fixture(scope="module", name="recordings")
def recordings_fixture(tmp_path_factory: pytest.TempPathFactory) -> Tuple[Path, ...]:
    """Two recordings sharing the long document's length, each a tone of its own, written once for the module."""
    folder = tmp_path_factory.mktemp("recordings")
    config = Config()
    seconds = LONG_SECONDS / RECORDINGS
    times = np.arange(round(seconds * config.sample_rate)) / config.sample_rate
    paths: List[Path] = []
    for index in range(RECORDINGS):
        path = folder / f"take{index}.wav"
        tone = RECORDING_AMPLITUDE * np.sin(2.0 * np.pi * RECORDING_FREQUENCY * (index + 1) * times)
        write_wave(path, config.sample_rate, tone.astype(np.float32))
        paths.append(path)

    return tuple(paths)


class TestWhatAnEditCosts:
    """Readings of what one edit costs the worker and the render thread, beside what a cold opening costs.

    The readings hold the edit path to nothing; they are what a change to it is judged by, taken on
    this meter before and after the change. Each case lands a burst of edits of one channel the way
    a drag lands them, one after the other, and reports the median and the least of each side's
    seconds. A project sample carries the strict history's fingerprint on each landing; a standalone
    document with its recordings read carries the original mix and, with a recording muted, the
    filtered reading.
    """

    @pytest.mark.parametrize("seconds", [SHORT_SECONDS, LONG_SECONDS], ids=["30s", "120s"])
    def test_a_project_sample_every_recording_heard(
        self,
        scheduling: SchedulingBehavior,
        seconds: float,
    ) -> None:
        meter = LandingMeter(scheduling)
        opening = meter.open_as_sample(long_document(seconds, config=Config()))
        before = meter.manager.reconstruction

        landings = [meter.edit(step) for step in range(1, EDITS + 1)]

        _report(f"project sample, {seconds:.0f} s, every recording heard", opening, landings, meter.renders.held_bytes)
        assert meter.manager.reconstruction is not before

    def test_a_standalone_document_with_a_recording_muted(
        self,
        scheduling: SchedulingBehavior,
        recordings: Tuple[Path, ...],
    ) -> None:
        meter = LandingMeter(scheduling)
        opening = meter.open_standalone(long_document(LONG_SECONDS, config=Config(), recordings=recordings))
        meter.mute(MUTED_STEM_ID)
        before = meter.manager.reconstruction

        landings = [meter.edit(step) for step in range(1, EDITS + 1)]

        _report(
            f"standalone document, {LONG_SECONDS:.0f} s, recordings read, one muted",
            opening,
            landings,
            meter.renders.held_bytes,
        )
        assert meter.manager.reconstruction is not before
