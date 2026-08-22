from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, FrozenSet, Optional, Protocol, Sequence, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.constants.conversion import MAX_STEM_SOURCES, MIN_CHANNEL_CAP
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.main.stems import (
    ConversionSetup,
    StemLevels,
    StemSource,
    derive_conversion_setup,
    effective_channels,
)
from sampletones_application.services.result import (
    ConversionResult,
    ServiceCancelled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.progress import SystemProgress
from sampletones_application.view_model.main.converter import (
    ACTIVE_PHASES,
    ConversionPhase,
    ConverterViewModel,
)
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.parallelization import ETAEstimator, TaskProgress
from sampletones_core.reconstructions.converter import (
    ConversionPlan,
    DirectoryConversion,
    GroupConversion,
    get_output_path,
    group_output_path,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.exceptions import NoFilesToProcessError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import to_path

SINGLE_JOB: Final[int] = 1


@dataclass(frozen=True)
class ConversionSuccess:
    """The outcome a completed conversion hands to its listener: the reconstructions it wrote.

    One written reconstruction is one the reader can open straight away; several are a batch,
    which the reader reaches as a folder."""

    written: Tuple[Path, ...]

    @property
    def is_single(self) -> bool:
        """One reconstruction was written, so it is the one a follow-up offer would load."""
        return len(self.written) == 1


class ConversionServiceProtocol(Protocol):
    """The slice of the conversion service the converter logic drives.

    Typing the collaborator structurally keeps the logic layer bound to the
    service's result contract alone; the composition root supplies the real
    service.
    """

    def subscribe(self, handler: Callable[[ConversionResult], None]) -> None: ...

    def start(self, config: Config, plan: ConversionPlan) -> None: ...

    def cancel(self) -> None: ...

    def cleanup(self) -> None: ...

    def shutdown(self) -> None: ...

    def is_running(self) -> bool: ...


class ConverterLogic(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        conversion_service: ConversionServiceProtocol,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
        is_operation_active: Callable[[], bool],
    ) -> None:
        self._language_manager = language_manager
        self._config_manager = config_manager
        self._service = conversion_service
        self._scheduling = scheduling
        self._is_operation_active = is_operation_active
        self._msg_idle = language_manager["main.converter.message.status_idle"]
        self._msg_cancelling = language_manager["main.converter.message.status_cancelling"]

        self._phase: ConversionPhase = ConversionPhase.IDLE
        self._input_path: Optional[Path] = None
        self._output_path: Optional[Path] = None
        self._written: Tuple[Path, ...] = ()
        self._is_file: bool = True
        self._stems_mode: bool = False
        self._levels: StemLevels = StemLevels()
        self._channel_cap: int = len(ChannelName)
        self._hierarchy_mode: HierarchyMode = DEFAULT_STEMS_HIERARCHY_MODE
        self._system_progress = SystemProgress()

        self._service.subscribe(self._on_service_result)

        self.on_view_changed: Optional[Callable[[ConverterViewModel], None]] = None
        self.on_success: Optional[Callable[[ConversionSuccess], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_no_files_to_process: Optional[VoidCallback] = None
        self.on_no_generators: Optional[VoidCallback] = None
        self.on_target_exists: Optional[PathCallback] = None
        self.on_load_file: Optional[PathCallback] = None
        self.on_load_directory: Optional[VoidCallback] = None
        self.on_cancelled: Optional[VoidCallback] = None
        self.generate_library: Optional[VoidCallback] = None
        self.cancel_library_generation: Optional[VoidCallback] = None
        self.is_library_available: Optional[Callable[[], bool]] = None

    @property
    def stems_mode(self) -> bool:
        """Several recordings are being gathered into one reconstruction."""
        return self._stems_mode

    @property
    def source_count(self) -> int:
        """How many recordings the stems list holds."""
        return self._levels.count

    @property
    def room_for_sources(self) -> int:
        """How many more recordings the stems list has room for."""
        return MAX_STEM_SOURCES - self.source_count

    @property
    def is_active(self) -> bool:
        """A conversion is occupying resources from the moment of request (the WAITING phase, during
        which the library is prepared and the run is scheduled) until it reaches a terminal phase."""
        return self._phase in ACTIVE_PHASES

    def emit_initial_view(self) -> None:
        self._emit_view_model(self._msg_idle, 0.0)

    def refresh_view(self) -> None:
        """Re-emits the idle view so the Convert button reflects whether another exclusive operation
        is active. Only the idle phase carries the Convert button; the other phases disable it by
        phase alone, so re-emitting them would add nothing."""
        if self._phase == ConversionPhase.IDLE:
            self._emit_view_model(self._msg_idle, 0.0)

    def set_input_path(self, input_path: Path, convert: bool = False) -> None:
        config = self._config_manager.config.model_copy()
        if not self._assign_paths(input_path, config):
            return

        if not self.is_active:
            self._phase = ConversionPhase.IDLE
            self._emit_view_model(self._msg_idle, 0.0)

        if convert:
            self.start_conversion()

    def select_source(self, path: Path) -> None:
        """Answers a recording picked in the explorer: it joins the list, or becomes the input.

        In stems mode a pick adds to the setup being built, so a reader gathers a conversion by
        clicking the recordings it mixes. Otherwise it is the single thing to convert.
        """
        if self._stems_mode:
            self.add_sources([path])
            return

        self.set_input_path(path)

    def add_sources(self, paths: Sequence[Path]) -> None:
        """Adds recordings to the stems list, up to the room it has left.

        A path already listed keeps the row it has, so adding it again leaves the setup as it is.
        """
        enabled = frozenset(self._config_manager.config.generation.channels)
        for path in paths:
            if self._levels.count >= MAX_STEM_SOURCES:
                break

            self._levels = self._levels.add(StemSource(path=path, channels=enabled))

        self._refresh_setup()

    def remove_source(self, path: Path) -> None:
        """Takes a recording out of the stems list."""
        self._levels = self._levels.remove(path)
        self._refresh_setup()

    def set_source_channels(self, path: Path, channels: FrozenSet[ChannelName]) -> None:
        """Names the channels one recording may take, among the ones the reader was offered.

        A channel the configuration leaves out reaches no checkbox, so the recording keeps
        whatever it was given for it and gets that choice back when the channel returns.
        """
        enabled = frozenset(self._config_manager.config.generation.channels)
        self._apply(
            self._levels.replace_source(
                path,
                lambda source: source.with_channels((source.channels - enabled) | channels),
            )
        )

    def move_source_within_level(self, path: Path, offset: int) -> None:
        """Moves a recording past the neighbour it shares a level with."""
        self._apply(self._levels.move_within_level(path, offset))

    def join_source_level(self, path: Path, offset: int) -> None:
        """Sends a recording to the level above or below the one it picks on."""
        self._apply(self._levels.join_level(path, offset))

    def isolate_source(self, path: Path) -> None:
        """Gives a recording a level of its own, picking after the one it shared."""
        self._apply(self._levels.isolate(path))

    def move_source_onto(self, path: Path, target_path: Path) -> None:
        """Moves a recording to the level and the place another one holds."""
        self._apply(self._levels.move_onto(path, target_path))

    def move_source_to_new_level(self, path: Path, position: int) -> None:
        """Gives a recording a level of its own, in the slot the levels are broken at."""
        self._apply(self._levels.move_to_new_level(path, position))

    def set_stems_mode(self, stems_mode: bool) -> None:
        """Switches between converting one selection and mixing several recordings into one.

        Entering stems mode carries a selected file in as the first row. Leaving it keeps the
        first row as the single selection, which is what the reader picked first.
        """
        if stems_mode == self._stems_mode:
            return

        self._stems_mode = stems_mode
        if stems_mode:
            self._enter_stems_mode()
        else:
            self._leave_stems_mode()

        self._refresh_setup()

    def set_channel_cap(self, channel_cap: int) -> None:
        """Names how many channels one recording may hold in a frame, for every conversion."""
        self._channel_cap = min(max(channel_cap, MIN_CHANNEL_CAP), self._max_channel_cap())
        self._refresh_setup()

    def set_hierarchy_mode(self, hierarchy_mode: HierarchyMode) -> None:
        """Names how the levels take turns: round by round, or one level exhausted before the next."""
        self._hierarchy_mode = hierarchy_mode
        self._refresh_setup()

    def start_conversion(self, confirmed: bool = False) -> None:
        """Starts the run the current setup describes, asking first where it would write over work.

        ``confirmed`` states that the reader has already answered for the file standing at the
        target, which is what lets the prompt's answer come back and run.
        """
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress")
            return

        if not self._config_manager.config.generation.channels:
            self.call(self.on_no_generators)
            return

        standing_target = self._standing_target()
        if standing_target is not None and not confirmed:
            self.call(self.on_target_exists, standing_target)
            return

        self._phase = ConversionPhase.WAITING
        self._emit_view_model(self._language_manager["main.converter.message.status_waiting"], 0.0)
        self.call(self.generate_library)
        self._wait_for_library_and_start()

    def cancel(self) -> None:
        if self._service.is_running():
            self._phase = ConversionPhase.CANCELLING
            self._emit_view_model(self._msg_cancelling, 0.0)
            self._system_progress.error()
            self._service.cancel()
        elif self._phase == ConversionPhase.WAITING:
            self.call(self.cancel_library_generation)
            self._on_cancellation_complete()

    def close(self) -> None:
        try:
            self._service.cleanup()
        finally:
            self._system_progress.clear()
            self._written = ()
            self._phase = ConversionPhase.IDLE
            self._emit_view_model(self._msg_idle, 0.0)

    def handle_load_request(self) -> None:
        if len(self._written) == 1:
            self.call(self.on_load_file, self._written[0])
        else:
            self.call(self.on_load_directory)

        self.close()

    def cleanup(self) -> None:
        self._service.shutdown()
        self._system_progress.clear()

    def _on_service_result(self, result: ConversionResult) -> None:
        match result:
            case ServiceStarted(total=total):
                self._system_progress.start(total)
            case ServiceProgress() as progress:
                self._handle_progress_result(progress)
            case ServiceIntermediate(data=progress):
                self._handle_library_progress(progress)
            case ServiceSuccess(value=written):
                self._on_conversion_complete(written)
            case ServiceError(exception=exception):
                self._on_conversion_error(exception)
            case ServiceCancelled():
                self._on_cancellation_complete()

    def _handle_progress_result(self, progress: ServiceProgress[Path]) -> None:
        if self._phase == ConversionPhase.CANCELLING:
            total = max(progress.total, 1)
            self._emit_view_model(
                self._msg_cancelling,
                progress.completed / total,
            )
            return

        self._phase = ConversionPhase.RUNNING
        self._system_progress.set(progress.completed, progress.total)
        eta_string = ETAEstimator.format_duration(progress.eta_seconds)
        total = max(progress.total, 1)
        status_text = self._compose_progress_text(progress)
        if eta_string:
            status_text += self._language_manager["global.dialog.template.time_estimation"].format(
                eta_string=eta_string
            )

        display_input_path = (
            to_path(str(progress.current_item)) if progress.current_item is not None else self._input_path
        )
        self._emit_view_model(
            status_text,
            progress.completed / total,
            input_path=display_input_path,
        )

    def _compose_progress_text(self, progress: ServiceProgress[Path]) -> str:
        """What the run is doing: the reconstruction being built, or how far a batch has come.

        A batch is many reconstructions and a count says where it stands; a single job counts to
        one, so it names the document it is writing instead.
        """
        if progress.total > SINGLE_JOB:
            return self._language_manager["main.converter.template.progress_template"].format(
                progress.completed, progress.total
            )

        return self._language_manager["main.converter.template.single_progress_template"].format(
            self._reconstruction_name()
        )

    def _reconstruction_name(self) -> str:
        """The document a single job writes, which is what a run of one is making."""
        if self._output_path is not None:
            return self._output_path.stem

        return self._input_path.stem if self._input_path is not None else ""

    def _handle_library_progress(self, progress: TaskProgress) -> None:
        if self._phase != ConversionPhase.WAITING:
            return

        total = max(progress.total, 1)
        fraction = progress.completed / total
        self._emit_view_model(self._language_manager["main.converter.message.status_generating_library"], fraction)

    def _assign_paths(self, input_path: Path, config: Config) -> bool:
        try:
            self._output_path = get_output_path(config, input_path)
            self._input_path = input_path
            self._is_file = input_path.is_file()
        except FileNotFoundError as exception:
            logger.error("Input file does not exist")
            self.call(self.on_error, exception)
            return False
        except OSError as exception:
            logger.error("Invalid path")
            self.call(self.on_error, exception)
            return False

        return True

    def _wait_for_library_and_start(self) -> None:
        if self._phase != ConversionPhase.WAITING:
            return

        if not self.call(self.is_library_available):
            CallbackQueue.add(
                self._wait_for_library_and_start,
                priority=self._scheduling.priorities.schedule,
                delay=self._scheduling.delays.schedule,
            )
        else:
            self._start_conversion()

    def _start_conversion(self) -> None:
        assert self._input_path is not None, "Input path is not set"
        config = self._config_manager.config.model_copy()
        self._system_progress.initialize()
        self._service.start(config, self._conversion_plan(config, self._input_path))

    def _standing_target(self) -> Optional[Path]:
        """The reconstruction this run would write over, where one stands.

        A batch converts what is still to be written and keeps the rest, so it puts nothing to
        the reader; a single conversion writes one file, and that is the one worth asking about.
        """
        if self._input_path is None:
            return None

        config = self._config_manager.config
        targets = self._conversion_plan(config, self._input_path).existing_targets(config)
        return targets[0] if targets else None

    def _conversion_plan(self, config: Config, input_path: Path) -> ConversionPlan:
        """What the request amounts to: one reconstruction from the recordings listed or the file
        selected, or one per audio file the selected directory holds."""
        setup = self._stems_setup(config)
        if self._stems_mode:
            return GroupConversion(sources=setup.sources, stems=setup.stems)

        if self._is_file:
            return GroupConversion(sources=(input_path,), stems=setup.stems)

        return DirectoryConversion(directory=input_path, stems=setup.stems)

    def _stems_setup(self, config: Config) -> ConversionSetup:
        """The recordings and the setup the conversion runs with, carrying the channel cap.

        In stems mode this is what the gathered levels amount to; otherwise it is one stem over
        every enabled channel, which is the classic run's shape.
        """
        enabled = list(config.generation.channels)
        if self._stems_mode:
            return derive_conversion_setup(
                self._levels,
                enabled,
                channel_cap=self._effective_channel_cap,
                hierarchy_mode=self._hierarchy_mode,
            )

        return ConversionSetup(
            sources=(),
            stems=StemsConfig.single_entry(enabled, channel_cap=self._effective_channel_cap),
        )

    @property
    def _source_paths(self) -> Tuple[Path, ...]:
        """The recordings that take part, in the order the conversion mixes them."""
        return self._stems_setup(self._config_manager.config).sources

    @property
    def _effective_channel_cap(self) -> int:
        """The cap a run holds to: what the reader asked for, within the channels now enabled."""
        return min(self._channel_cap, self._max_channel_cap())

    def _max_channel_cap(self) -> int:
        return max(len(self._config_manager.config.generation.channels), MIN_CHANNEL_CAP)

    def _apply(self, levels: StemLevels) -> None:
        """Takes up a rewritten stems list and follows it wherever the setup changed."""
        self._levels = levels
        self._refresh_setup()

    def _enter_stems_mode(self) -> None:
        enabled = frozenset(self._config_manager.config.generation.channels)
        if self._levels.count == 0 and self._input_path is not None and self._is_file:
            self._levels = self._levels.add(StemSource(path=self._input_path, channels=enabled))

    def _leave_stems_mode(self) -> None:
        if self._levels.count:
            self._levels = self._levels.keep_first()
            self._assign_paths(self._levels.paths[0], self._config_manager.config)

    def _refresh_setup(self) -> None:
        """Follows the setup wherever it changed: the destination it now names, and the view."""
        self._update_stems_output_path()
        if not self.is_active:
            self._phase = ConversionPhase.IDLE
            self._emit_view_model(self._msg_idle, 0.0)

    def _update_stems_output_path(self) -> None:
        if not self._stems_mode:
            return

        sources = self._source_paths
        if sources:
            self._output_path = group_output_path(self._config_manager.config, sources)

    def _stem_rows(self, config: Config) -> Tuple[StemRowViewModel, ...]:
        """The gathered recordings as the panel reads them, each stating where it stands.

        A gathered recording is named by its path, so the list reports every gesture under the
        path it landed on, and it offers a box on every channel the configuration enables. A
        recording that has left the disk since it was gathered reports itself as missing.
        """
        enabled = list(config.generation.channels)
        return tuple(
            StemRowViewModel(
                key=str(source.path),
                path=source.path,
                channels=frozenset(effective_channels(source, enabled)),
                offered_channels=frozenset(enabled),
                available=source.path.is_file(),
                level=level_index,
                position=position,
                level_size=len(level),
                level_count=self._levels.level_count,
            )
            for level_index, level in enumerate(self._levels.levels)
            for position, source in enumerate(level)
        )

    def _on_conversion_complete(self, written: Tuple[Path, ...]) -> None:
        self._written = written
        if len(written) == 1:
            self._output_path = written[0]

        self._phase = ConversionPhase.COMPLETED
        self._emit_view_model(self._language_manager["main.converter.message.status_reconstruction_completed"], 1.0)
        self.call(self.on_success, ConversionSuccess(written=written))

    def _on_conversion_error(self, exception: Exception) -> None:
        self._system_progress.error()
        self._phase = ConversionPhase.FAILED
        self._emit_view_model(self._language_manager["main.converter.message.status_error"], 0.0)
        self._schedule_return_to_idle()
        if isinstance(exception, NoFilesToProcessError):
            self.call(self.on_no_files_to_process)
        else:
            self.call(self.on_error, exception)

    def _on_cancellation_complete(self) -> None:
        self._phase = ConversionPhase.CANCELLED
        self._emit_view_model(self._language_manager["main.converter.message.status_cancelled"], 0.0)
        self._schedule_return_to_idle()
        self.call(self.on_cancelled)

    def _schedule_return_to_idle(self) -> None:
        CallbackQueue.add(
            self.close,
            priority=self._scheduling.priorities.schedule,
            delay=self._scheduling.delays.cancel,
        )

    def _compose_action_label(self, input_path: Optional[Path]) -> str:
        """The label the single action button shows: the cancel label while a conversion holds
        resources, otherwise the convert label named after what it would convert."""
        if self._phase in ACTIVE_PHASES:
            return self._language_manager["main.converter.label.cancel_button"]

        if self._stems_mode:
            return self._compose_stems_action_label()

        base = (
            self._language_manager["main.converter.label.convert_sample_button"]
            if self._is_file
            else self._language_manager["main.converter.label.convert_directory_button"]
        )
        if input_path is None:
            return base

        return self._language_manager["main.converter.template.convert_label_template"].format(base, input_path.name)

    def _compose_stems_action_label(self) -> str:
        """The stems label, named after how many recordings take part."""
        base = self._language_manager["main.converter.label.convert_stems_button"]
        playing = len(self._source_paths)
        if not playing:
            return base

        return self._language_manager["main.converter.template.convert_label_template"].format(base, playing)

    def _emit_view_model(
        self,
        status_text: str,
        progress: float,
        input_path: Optional[Path] = None,
    ) -> None:
        config = self._config_manager.config
        display_output = (
            self._output_path if self._output_path is not None else self._config_manager.get_reconstructions_directory()
        )
        display_input = input_path if input_path is not None else self._input_path
        view_model = ConverterViewModel(
            phase=self._phase,
            status_text=status_text,
            action_label=self._compose_action_label(display_input),
            progress=progress,
            input_path=display_input,
            output_path=display_output,
            is_file=self._is_file,
            other_operation_active=self._is_operation_active(),
            stems_mode=self._stems_mode,
            stem_sources=self._stem_rows(config),
            enabled_channels=frozenset(config.generation.channels),
            channel_cap=self._effective_channel_cap,
            max_channel_cap=self._max_channel_cap(),
            hierarchy_mode=self._hierarchy_mode,
            max_sources=MAX_STEM_SOURCES,
        )
        self.call(self.on_view_changed, view_model)
