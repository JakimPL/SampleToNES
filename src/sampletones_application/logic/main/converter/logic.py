from pathlib import Path
from typing import Callable, FrozenSet, Optional, Sequence

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
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
    conversion_plan,
    playing_sources,
)
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.converter.view import compose_view
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
                stems_mode=False,
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
    def stems_mode(self) -> bool:
        """Several recordings are being gathered into one reconstruction."""
        return self._state.settings.stems_mode

    @property
    def source_count(self) -> int:
        """How many recordings the stems list holds."""
        return self._state.gathering.count

    @property
    def room_for_sources(self) -> int:
        """How many more recordings the stems list has room for."""
        return self._state.gathering.room

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

    def set_input_path(self, input_path: Path, convert: bool = False) -> None:
        destination = self._aimed_at(self._state, input_path)
        if destination is None:
            return

        self._state = self._state.with_destination(destination)
        if not self.is_active:
            self._run.return_to_idle()
            self._emit(self._messages.idle, 0.0)

        if convert:
            self.start_conversion()

    def select_source(self, path: Path) -> None:
        """Answers a recording picked in the explorer: it joins the list, or becomes the input.

        In stems mode a pick adds to the setup being built, so a reader gathers a conversion by
        clicking the recordings it mixes. Otherwise it is the single thing to convert.
        """
        if self.stems_mode:
            self.add_sources([path])
            return

        self.set_input_path(path)

    def add_sources(self, paths: Sequence[Path]) -> None:
        """Adds recordings to the stems list, up to the room it has left.

        A path already listed keeps the row it has, so adding it again leaves the setup as it is.
        """
        gathering = self._state.gathering
        for path in paths:
            gathering = gathering.add(self._gathered(path))

        self._settle(self._state.with_gathering(gathering))

    def remove_source(self, path: Path) -> None:
        """Takes a recording out of the stems list."""
        self._settle(self._state.with_gathering(self._state.gathering.remove(path)))

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

    def set_stems_mode(self, stems_mode: bool) -> None:
        """Switches between converting one selection and mixing several recordings into one.

        Entering stems mode carries a selected file in as the first row. Leaving it keeps the
        first row as the single selection, which is what the reader picked first.
        """
        if stems_mode == self.stems_mode:
            return

        state = self._state.with_settings(self._settings.with_stems_mode(stems_mode))
        self._settle(self._entered(state) if stems_mode else self._left(state))

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

    @property
    def _joining_settings(self) -> StemSettings:
        """What a recording is converted with when it joins the list, as the reader last left it."""
        return self._settings.joining

    def _aimed_at(self, state: ConverterState, input_path: Path) -> Optional[Destination]:
        """Where a newly picked path would write, or nothing where the path cannot be read."""
        config = self._config_manager.config.model_copy()
        try:
            return state.destination.aimed_at(config, input_path, state.settings.enabled_channels)
        except FileNotFoundError as exception:
            logger.error("Input file does not exist")
            self.call(self.on_error, exception)
        except OSError as exception:
            logger.error("Invalid path")
            self.call(self.on_error, exception)

        return None

    def _entered(self, state: ConverterState) -> ConverterState:
        """The setup a mix opens with: the file the reader picked, where they picked one."""
        destination = state.destination
        if state.gathering.count or destination.input_path is None or not destination.is_file:
            return state

        return state.with_gathering(state.gathering.add(self._gathered(destination.input_path)))

    def _left(self, state: ConverterState) -> ConverterState:
        """The setup a mix leaves behind: the recording that picked first, as the single input."""
        if not state.gathering.count:
            return state

        gathering = state.gathering.kept_first()
        destination = self._aimed_at(state, gathering.paths[0])
        state = state.with_gathering(gathering)
        return state if destination is None else state.with_destination(destination)

    def _relevel(self, levels: MixLevels) -> None:
        """Takes up rewritten levels and follows them wherever the setup changed."""
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
        if not state.settings.stems_mode:
            return state

        return state.with_destination(
            state.destination.aimed_at_mix(
                self._config_manager.config,
                playing_sources(state),
                state.settings.enabled_channels,
            )
        )

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
            stems_mode=self.stems_mode,
            is_file=destination.is_file,
            input_path=input_path,
            playing=len(playing_sources(self._state)),
        )
