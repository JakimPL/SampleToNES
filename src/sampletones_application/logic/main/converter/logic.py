from pathlib import Path
from typing import Callable, FrozenSet, Optional, Sequence, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.constants.output import OutputKind
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.messages import ConverterMessages
from sampletones_application.logic.main.converter.run import (
    ConversionRun,
    ConversionServiceProtocol,
    ConversionSuccess,
    RunReport,
)
from sampletones_application.logic.main.converter.settings import RunSettings
from sampletones_application.logic.main.converter.setup import (
    batch_entries,
    conversion_plan,
    playing_sources,
)
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.converter.view import compose_view
from sampletones_application.logic.main.sources.folder import Folder
from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.levels import MixLevels
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_application.logic.main.sources.slots import CHANNEL_SLOT
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterViewModel,
)
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.converter import ConversionPlan
from sampletones_core.reconstructions.converter.paths import top_level_audio_files
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.exceptions import NoFilesToProcessError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class ConverterLogic(CallbackMixin):
    """What the Main tab's converter offers, and the one place its parts are settled against.

    The setup a reader builds is one value (:class:`ConverterState`), and every gesture rewrites a
    part of it and hands the whole back to ``_settle``, which follows it wherever it reaches: the
    destination the run now names, and the view the panel draws. The run itself is held apart, so
    a conversion under way reports where it stands without knowing what it was set up from.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        conversion_service: ConversionServiceProtocol,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
        is_operation_active: Callable[[], bool],
    ) -> None:
        self._config_manager = config_manager
        self._session_manager = session_manager
        self._scheduling = scheduling
        self._is_operation_active = is_operation_active
        self._messages = ConverterMessages(language_manager)
        self._state = ConverterState(
            settings=RunSettings(
                joining=session_manager.converter_settings,
                output=OutputKind.PER_RECORDING,
                channel_cap=len(ChannelName),
                hierarchy_mode=DEFAULT_STEMS_HIERARCHY_MODE,
            ),
            gathering=Gathering.empty(),
            destination=Destination.unset(),
        )

        self._run = ConversionRun(conversion_service, messages=self._messages)
        self._run.on_report = self._on_report
        self._run.on_success = self._on_run_success
        self._run.on_error = self._on_run_error
        self._run.on_canceled = self._on_run_canceled

        self.on_view_changed: Optional[Callable[[ConverterViewModel], None]] = None
        self.on_success: Optional[Callable[[ConversionSuccess], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_no_files_to_process: Optional[VoidCallback] = None
        self.on_no_generators: Optional[VoidCallback] = None
        self.on_target_exists: Optional[PathCallback] = None
        self.on_load_file: Optional[PathCallback] = None
        self.on_load_directory: Optional[VoidCallback] = None
        self.on_canceled: Optional[VoidCallback] = None
        self.generate_library: Optional[VoidCallback] = None
        self.cancel_library_generation: Optional[VoidCallback] = None
        self.is_library_available: Optional[Callable[[], bool]] = None

    @property
    def mixes(self) -> bool:
        """Several recordings are being gathered into one reconstruction."""
        return self._settings.mixes

    @property
    def source_count(self) -> int:
        """How many recordings the stems list holds."""
        return self._state.gathering.count

    @property
    def room_for_sources(self) -> int:
        """How many more recordings the mix has room for."""
        return self._state.gathering.room

    @property
    def gathered_paths(self) -> Tuple[Path, ...]:
        """Every gathered recording, which is what a reader picking a mix is offered."""
        return self._state.gathering.paths

    @property
    def is_active(self) -> bool:
        """A conversion is occupying resources, from the request until it settles."""
        return self._run.is_active

    def emit_initial_view(self) -> None:
        self._emit(self._messages.idle, 0.0)

    def refresh_view(self) -> None:
        """Re-emits the idle view so the Convert button reflects whether another exclusive operation
        is active. Only the idle phase carries the Convert button; the other phases disable it by
        phase alone, so re-emitting them would add nothing."""
        if self._run.phase == ConversionPhase.IDLE:
            self._emit(self._messages.idle, 0.0)

    def gather_recordings(self, paths: Sequence[Path]) -> None:
        """Gathers recordings into the setup, each converted under what a recording joins with.

        A path already gathered keeps the row and the settings it has. A mix reaches a fixed
        number of recordings, so a full one takes no more; a per-recording run takes whatever is
        offered, which is what converting a whole folder amounts to.
        """
        gathering = self._state.gathering
        for path in paths:
            gathering = self._joined(gathering, self._gathered(path))

        self._settle(self._state.with_gathering(gathering))

    def gather_folder(self, root: Path) -> None:
        """Gathers a folder, standing for every recording found directly below it.

        A run writing one reconstruction per recording mirrors this folder's tree for what it
        holds; a mix takes the recordings loose, which is what flattening leaves.
        """
        recordings = [self._gathered(path) for path in top_level_audio_files(root)]
        if not recordings:
            return

        if self.mixes:
            self.gather_recordings([recording.path for recording in recordings])
            return

        folder = Folder(root=root, recordings=tuple(recordings))
        self._settle(self._state.with_gathering(self._state.gathering.listing_folder(folder)))

    def convert_path(self, path: Path) -> None:
        """Converts exactly what the reader named, which is what a Reconstruct asks for.

        The setup becomes that one source — a recording, or a folder standing for the recordings
        below it — and the run starts, writing one reconstruction apiece.
        """
        self._settle(
            self._state.with_settings(self._settings.with_output(OutputKind.PER_RECORDING)).with_gathering(
                Gathering.empty()
            )
        )
        if path.is_dir():
            self.gather_folder(path)
        else:
            self.gather_recordings([path])

        self.start_conversion()

    def remove_source(self, path: Path) -> None:
        """Takes one gathered recording out of the setup."""
        self._settle(self._state.with_gathering(self._state.gathering.remove(SourceKey.recording(path))))

    def remove_folder(self, root: Path) -> None:
        """Takes a folder out of the setup, along with every recording it stands for."""
        self._settle(self._state.with_gathering(self._state.gathering.remove(SourceKey.folder(root))))

    def set_source_channels(self, path: Path, channels: FrozenSet[ChannelName]) -> None:
        """Names the channels one recording may take, among the ones the reader was offered."""
        gathering = self._state.gathering.written_among(
            path,
            CHANNEL_SLOT,
            channels,
            self._settings.enabled_channels,
        )
        self._settle(self._state.with_gathering(gathering))

    def move_source_within_level(self, path: Path, offset: int) -> None:
        """Moves a recording past the neighbor it shares a level with."""
        self._relevel(self._state.gathering.levels.move_within_level(path, offset))

    def join_source_level(self, path: Path, offset: int) -> None:
        """Sends a recording to the level above or below the one it picks on."""
        self._relevel(self._state.gathering.levels.join_level(path, offset))

    def isolate_source(self, path: Path) -> None:
        """Gives a recording a level of its own, picking after the one it shared."""
        self._relevel(self._state.gathering.levels.isolate(path))

    def move_source_onto(self, path: Path, target_path: Path) -> None:
        """Moves a recording to the level and the place another one holds."""
        self._relevel(self._state.gathering.levels.move_onto(path, target_path))

    def move_source_to_new_level(self, path: Path, position: int) -> None:
        """Gives a recording a level of its own, in the slot the levels are broken at."""
        self._relevel(self._state.gathering.levels.move_to_new_level(path, position))

    def set_output(self, output: OutputKind) -> None:
        """Names what the run writes: one reconstruction per recording, or one from them all.

        A mix converts loose recordings and holds a fixed number of them, so turning to one
        flattens the folders standing in the list and keeps what fits. Turning away leaves the
        list as it is and lets the picking order go.
        """
        if output == self._settings.output:
            return

        gathering = self._state.gathering
        settled = gathering.mixing_only(gathering.paths[:MAX_STEM_SOURCES]) if output.mixes else gathering.unmixed()
        self._settle(self._state.with_settings(self._settings.with_output(output)).with_gathering(settled))

    def mix_only(self, paths: Sequence[Path]) -> None:
        """Names the recordings a mix converts, which is what a reader answers a full mix with."""
        gathering = self._state.gathering.mixing_only(tuple(paths)[:MAX_STEM_SOURCES])
        self._settle(self._state.with_settings(self._settings.with_output(OutputKind.MIXED)).with_gathering(gathering))

    def set_joining_channels(self, channels: FrozenSet[ChannelName]) -> None:
        """Names the channels a recording holds when it joins the list, carried between runs.

        A run hands out what a recording joins with, so narrowing this narrows every gathered
        recording to the channels still named; each keeps the choice it was given for a channel
        left out and gets it back when that channel returns.
        """
        settings = self._settings.with_joining_channels(channels)
        self._session_manager.set_converter_settings(settings.joining)
        self._settle(self._state.with_settings(settings))

    def set_channel_cap(self, channel_cap: int) -> None:
        """Names how many channels one recording may hold in a frame, for every conversion."""
        self._settle(self._state.with_settings(self._settings.with_channel_cap(channel_cap)))

    def set_hierarchy_mode(self, hierarchy_mode: HierarchyMode) -> None:
        """Names how the levels take turns: round by round, or one level exhausted before the next."""
        self._settle(self._state.with_settings(self._settings.with_hierarchy_mode(hierarchy_mode)))

    def start_conversion(self, confirmed: bool = False) -> None:
        """Starts the run the current setup describes, asking first where it would write over work.

        ``confirmed`` states that the reader has already answered for the file standing at the
        target, which is what lets the prompt's answer come back and run.
        """
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress")
            return

        if not self._settings.enabled_channels:
            self.call(self.on_no_generators)
            return

        plan = conversion_plan(self._state)
        if plan is None:
            logger.warning("Nothing is selected to convert")
            return

        standing_target = self._standing_target(plan)
        if standing_target is not None and not confirmed:
            self.call(self.on_target_exists, standing_target)
            return

        self._run.wait()
        self.call(self.generate_library)
        self._wait_for_library_and_start()

    def cancel(self) -> None:
        if self._run.is_running:
            self._run.cancel()
        elif self._run.phase == ConversionPhase.WAITING:
            self.call(self.cancel_library_generation)
            self._run.abandon()

    def close(self) -> None:
        try:
            self._run.close()
        finally:
            self._emit(self._messages.idle, 0.0)

    def handle_load_request(self) -> None:
        written = self._run.written
        if len(written) == 1:
            self.call(self.on_load_file, written[0])
        else:
            self.call(self.on_load_directory)

        self.close()

    def cleanup(self) -> None:
        self._run.cleanup()

    @property
    def _settings(self) -> RunSettings:
        return self._state.settings

    def _gathered(self, path: Path) -> Recording:
        """A recording joining the list, holding the settings a recording joins with."""
        return Recording(path=path, settings=self._joining_settings)

    def _joined(self, gathering: Gathering, recording: Recording) -> Gathering:
        """One more recording in the setup, joining the mix where the run is one."""
        return gathering.mixing(recording) if self.mixes else gathering.listing(recording)

    @property
    def _joining_settings(self) -> StemSettings:
        """What a recording is converted with when it joins the list, as the reader last left it."""
        return self._settings.joining

    def _relevel(self, levels: MixLevels) -> None:
        """Takes up rewritten levels and follows them wherever the setup changed.

        The levels are the mix's own order, so a run writing one reconstruction apiece has none to
        rewrite and a gesture reaching it changes nothing.
        """
        if not self.mixes:
            return

        self._settle(self._state.with_gathering(self._state.gathering.with_levels(levels)))

    def _settle(self, state: ConverterState) -> None:
        """Takes up a rewritten setup and follows it wherever it reaches.

        A mix names its destination after the recordings that take part, so the path the panel
        shows follows every gesture; a settled run returns to idle, since the setup it reported on
        is no longer the one on screen.
        """
        self._state = self._redirected(state)
        if not self.is_active:
            self._run.return_to_idle()
            self._emit(self._messages.idle, 0.0)

    def _redirected(self, state: ConverterState) -> ConverterState:
        """The setup with its destination following the sources that take part in it."""
        config = self._config_manager.config
        channels = state.settings.enabled_channels
        destination = state.destination.named_after(state.gathering.sources)
        if state.settings.mixes:
            return state.with_destination(destination.aimed_at_mix(config, playing_sources(state), channels))

        return state.with_destination(destination.aimed_at_batch(config, batch_entries(state), channels))

    def _standing_target(self, plan: ConversionPlan) -> Optional[Path]:
        """The reconstruction ``plan`` would write over, where one stands.

        A batch converts what is still to be written and keeps the rest, so it puts nothing to
        the reader; a run writing one document asks about that document.
        """
        targets = plan.existing_targets(self._config_manager.config)
        return targets[0] if targets else None

    def _wait_for_library_and_start(self) -> None:
        if self._run.phase != ConversionPhase.WAITING:
            return

        if not self.call(self.is_library_available):
            CallbackQueue.add(
                self._wait_for_library_and_start,
                priority=self._scheduling.priorities.schedule,
                delay=self._scheduling.delays.schedule,
            )
        else:
            self._begin_conversion()

    def _begin_conversion(self) -> None:
        plan = conversion_plan(self._state)
        if plan is None:
            logger.warning("Nothing is selected to convert")
            return

        config: Config = self._config_manager.config.model_copy()
        self._run.begin(config, plan, self._state.destination.reconstruction_name)

    def _on_report(self, report: RunReport) -> None:
        self._emit(report.status_text, report.progress, running_input=report.input_path)

    def _on_run_success(self, success: ConversionSuccess) -> None:
        if success.is_single:
            self._state = self._state.with_destination(self._state.destination.writing_to(success.written[0]))

        self.call(self.on_success, success)

    def _on_run_error(self, exception: Exception) -> None:
        self._schedule_return_to_idle()
        if isinstance(exception, NoFilesToProcessError):
            self.call(self.on_no_files_to_process)
        else:
            self.call(self.on_error, exception)

    def _on_run_canceled(self) -> None:
        self._schedule_return_to_idle()
        self.call(self.on_canceled)

    def _schedule_return_to_idle(self) -> None:
        CallbackQueue.add(
            self.close,
            priority=self._scheduling.priorities.schedule,
            delay=self._scheduling.delays.cancel,
        )

    def _emit(
        self,
        status_text: str,
        progress: float,
        running_input: Optional[Path] = None,
    ) -> None:
        view_model = compose_view(
            self._state,
            phase=self._run.phase,
            status_text=status_text,
            action_label=self._action_label(running_input),
            progress=progress,
            running_input=running_input,
            reconstructions_directory=self._config_manager.get_reconstructions_directory(),
            other_operation_active=self._is_operation_active(),
        )
        self.call(self.on_view_changed, view_model)

    def _action_label(self, running_input: Optional[Path]) -> str:
        destination = self._state.destination
        input_path = running_input if running_input is not None else destination.input_path
        return self._messages.action_label(
            phase=self._run.phase,
            mixes=self.mixes,
            is_file=destination.is_file,
            input_path=input_path,
            playing=len(playing_sources(self._state)),
        )
