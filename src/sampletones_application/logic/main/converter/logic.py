from pathlib import Path
from typing import Callable, FrozenSet, Optional, Sequence, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.output import OutputKind
from sampletones_application.constants.sources import SettingsField, SourceKind
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
    conversion_setup,
    playing_sources,
)
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.converter.view import (
    compose_view,
    inspected_settings,
    inspected_source,
    settings_slots,
    stem_rows,
)
from sampletones_application.logic.main.sources.folder import Folder
from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.levels import MixLevels
from sampletones_application.logic.main.sources.list import SourceList
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_application.logic.main.sources.slots import (
    CHANNEL_SLOT,
    SLOTS_BY_FIELD,
    SettingsSlot,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterViewModel,
)
from sampletones_application.view_model.main.reconstructor import (
    InspectedSourceViewModel,
    SettingsSlotViewModel,
)
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.converter import ConversionPlan
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.exceptions import NoFilesToProcessError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, PathsCallback, VoidCallback
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
                output=session_manager.converter_output,
                channel_cap=session_manager.converter_channel_cap,
                hierarchy_mode=session_manager.converter_hierarchy_mode,
            ),
            gathering=Gathering.empty(),
            destination=Destination.unset(),
            selected=None,
        )
        self._rows = self._read_rows()

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
        self.on_target_exists: Optional[PathsCallback] = None
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
    def mix_ceiling(self) -> int:
        """How many recordings one mix reaches, which is the room a reader picks one within."""
        return self._state.gathering.ceiling

    @property
    def list_fits_a_mix(self) -> bool:
        """One mix has room for the whole list, so turning to one takes it as it stands."""
        return self._state.gathering.fits_a_mix

    @property
    def gathered_paths(self) -> Tuple[Path, ...]:
        """Every gathered recording, which is what a run writing one apiece converts."""
        return self._state.gathering.paths

    @property
    def gathered_rows(self) -> Tuple[StemRowViewModel, ...]:
        """The gathered sources as one run of rows, which is what a reader picking a mix reads."""
        return stem_rows(self._state.gathering, mixes=False)

    def rows_offered(self, found: Sequence[Path]) -> Tuple[StemRowViewModel, ...]:
        """The recordings among ``found`` the setup has yet to gather, as one row apiece.

        A mix reaches a fixed number of recordings, so a folder bringing in more than the room
        left is put to a reader as the same question the output switch asks: which of these to mix.
        The rows are what the folder offers, which the question stands beside the recordings the
        mix is built from so that the reader chooses between the two.
        """
        standing = frozenset(self.gathered_paths)
        offered = tuple(self._gathered(path) for path in found if path not in standing)
        return stem_rows(Gathering(sources=SourceList(rows=offered), levels=MixLevels()), mixes=False)

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

    def gather_folder(self, root: Path, found: Sequence[Path]) -> None:
        """Gathers a folder standing for the recordings ``found`` below it.

        A run writing one reconstruction per recording mirrors this folder's tree for what it
        holds; a mix takes the recordings loose, which is what flattening leaves. The recordings
        are handed in because reading them off the disk is work of its own, reported to the reader
        while it runs.
        """
        if self.mixes:
            self.gather_recordings(found)
            return

        self._settle(self._state.with_gathering(self._gathering_folder(root, found)))

    def convert_recording(self, path: Path) -> None:
        """Converts exactly the recording the reader named, which is what a Reconstruct asks for."""
        self._replace_setup()
        self.gather_recordings([path])
        self.start_conversion()

    def convert_folder(self, root: Path, found: Sequence[Path]) -> None:
        """Converts the recordings ``found`` below a folder, writing one reconstruction apiece."""
        self._replace_setup()
        self.gather_folder(root, found)
        self.start_conversion()

    def _replace_setup(self) -> None:
        """Lets whatever was gathered go, since a Reconstruct names what it converts on its own."""
        self._settle(
            self._state.with_settings(self._settings.with_output(OutputKind.PER_RECORDING)).with_gathering(
                Gathering.empty()
            )
        )

    def select_row(self, path: Path, kind: SourceKind) -> None:
        """Names the row a reader is inspecting, which the settings card edits."""
        self._settle(self._state.with_selected(SourceKey(kind=kind, path=path)))

    def clear_selection(self) -> None:
        """Lets the inspected row go, so the card edits what a recording joins the list with."""
        self._settle(self._state.with_selected(None))

    def remove_source(self, path: Path) -> None:
        """Takes one gathered recording out of the setup."""
        self._settle(self._state.with_gathering(self._state.gathering.remove(SourceKey.recording(path))))

    def remove_folder(self, root: Path) -> None:
        """Takes a folder out of the setup, along with every recording it stands for."""
        self._settle(self._state.with_gathering(self._state.gathering.remove(SourceKey.folder(root))))

    @property
    def settings_slots(self) -> Tuple[SettingsSlotViewModel, ...]:
        """The choices the settings card edits, read from the row a reader picked."""
        return settings_slots(self._state)

    @property
    def inspected_source(self) -> Optional[InspectedSourceViewModel]:
        """The row the settings card is editing, where a reader picked one out of the list."""
        return inspected_source(self._state)

    @property
    def live(self) -> bool:
        """Whether a gesture reaches the setup, which a conversion holding resources answers."""
        return not self._run.is_active

    def toggle_slot(self, field: SettingsField, channel_name: ChannelName) -> None:
        """Settles one choice on ``channel_name`` for the row the settings card is pointed at.

        A picked row settles the same way a folder's own box does — already agreeing lets the
        choice go, every other reading takes it up — so one gesture answers for a folder and for
        a recording alike.
        """
        selected = self._state.selected
        if selected is None:
            return

        slot = SLOTS_BY_FIELD[field]
        held = self._inspected_agreement(slot, channel_name).settles_to
        self._settle(self._state.with_gathering(self._state.gathering.settled(selected, slot, channel_name, held)))

    def toggle_channel(self, channel_name: ChannelName) -> None:
        """Switches one channel across the whole list, which is what the channel's key reaches.

        The list answers as one group: where every listed recording already holds the channel it
        goes from each, and otherwise it reaches the ones standing without it, so one press always
        leaves the list agreeing.
        """
        gathering = self._state.gathering.toggled_throughout(CHANNEL_SLOT, channel_name)
        self._settle(self._state.with_gathering(gathering))

    def set_source_channels(self, path: Path, channels: FrozenSet[ChannelName]) -> None:
        """Names the channels one recording may take, which is the whole of what it reaches."""
        gathering = self._state.gathering.written(path, CHANNEL_SLOT, channels)
        self._settle(self._state.with_gathering(gathering))

    def toggle_folder_channel(self, root: Path, channel_name: ChannelName) -> None:
        """Settles one channel on every recording a folder stands for, in one gesture.

        A folder its recordings already agree on lets the channel go; every other reading settles
        the whole folder on it, so one gesture always moves the group somewhere.
        """
        gathering = self._state.gathering.toggled(SourceKey.folder(root), CHANNEL_SLOT, channel_name)
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
        settled = (
            gathering.mixing_only(gathering.recordings[: gathering.ceiling]) if output.mixes else gathering.unmixed()
        )
        self._settle(self._state.with_settings(self._settings.with_output(output)).with_gathering(settled))

    def mix_only(self, paths: Sequence[Path]) -> None:
        """Names the recordings a mix converts, gathering the ones the list does not hold yet.

        This is the answer to both places a mix is put to the reader: narrowing a list longer than
        one holds, and choosing between what the mix stands on and what a folder offers beside it.
        Either way the answer names the whole mix, so what it leaves out goes and what it names
        joins — a recording already listed keeping the settings it has.
        """
        gathering = self._state.gathering
        mixed = tuple(self._standing(gathering, path) for path in tuple(paths)[: gathering.ceiling])
        self._settle(
            self._state.with_settings(self._settings.with_output(OutputKind.MIXED)).with_gathering(
                gathering.mixing_only(mixed)
            )
        )

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

        if not self._state.gathering.count:
            logger.warning("Nothing is gathered to convert")
            return

        plan = conversion_plan(self._state)
        if plan is None:
            self.call(self.on_no_generators)
            return

        standing_targets = self._standing_targets(plan)
        if standing_targets and not confirmed:
            self.call(self.on_target_exists, standing_targets)
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

    def _inspected_agreement(self, slot: SettingsSlot, channel_name: ChannelName) -> Agreement:
        """How the settings the card is editing read on ``channel_name`` in ``slot``."""
        return Agreement.over(channel_name in slot.read(settings) for settings in inspected_settings(self._state))

    def _gathered(self, path: Path) -> Recording:
        """A recording joining the list, holding the settings a recording joins with."""
        return Recording(path=path, settings=self._joining_settings)

    def _standing(self, gathering: Gathering, path: Path) -> Recording:
        """The recording ``path`` names: the one the list holds, or one joining it."""
        recording = gathering.recording(path)
        return recording if recording is not None else self._gathered(path)

    def _gathering_folder(self, root: Path, found: Sequence[Path]) -> Gathering:
        """The setup with ``root`` standing as one row, or as it stands where the folder is empty."""
        recordings = tuple(self._gathered(path) for path in found)
        if not recordings:
            return self._state.gathering

        return self._state.gathering.listing_folder(Folder(root=root, recordings=recordings))

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
        self._remember(state.settings)
        self._state = self._redirected(state.selecting(state.selected))
        self._rows = self._read_rows()
        if not self.is_active:
            self._run.return_to_idle()
            self._emit(self._messages.idle, 0.0)

    def _remember(self, settings: RunSettings) -> None:
        """Write down the shape of the run, so a launch opens where the last one left off.

        The settings a recording joins with and the run's own shape are carried between launches,
        which is what makes the converter open on the setup the reader last worked in.
        """
        if settings == self._settings:
            return

        self._session_manager.set_converter_settings(settings.joining)
        self._session_manager.set_converter_output(settings.output)
        self._session_manager.set_converter_channel_cap(settings.channel_cap)
        self._session_manager.set_converter_hierarchy_mode(settings.hierarchy_mode)

    def _redirected(self, state: ConverterState) -> ConverterState:
        """The setup with its destination following the sources that take part in it."""
        config = self._config_manager.config
        destination = state.destination.named_after(state.gathering.sources)
        if state.settings.mixes:
            setup = conversion_setup(state)
            return state.with_destination(destination.aimed_at_mix(config, setup.sources, setup.stems.covered_channels))

        return state.with_destination(destination.aimed_at_batch(config, batch_entries(state)))

    def _standing_targets(self, plan: ConversionPlan) -> Tuple[Path, ...]:
        """Every reconstruction ``plan`` would write over, in the order the run reaches them.

        A recording gathered from a folder is left where its reconstruction already stands, so a
        repeated folder run picks up where the last one stopped and puts nothing to the reader.
        A recording the reader named is written whenever the run goes, so all of those are named
        together: the answer covers each one it is given.
        """
        return plan.existing_targets(self._config_manager.config)

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
            action_label=self._action_label(),
            progress=progress,
            running_input=running_input,
            reconstructions_directory=self._config_manager.get_reconstructions_directory(),
            other_operation_active=self._is_operation_active(),
            rows=self._rows,
        )
        self.call(self.on_view_changed, view_model)

    def _read_rows(self) -> Tuple[StemRowViewModel, ...]:
        """The gathered sources as the list draws them, read once for the setup now standing.

        Reading a row reaches the disk for whether its recording is still there, and a folder is
        read down to the recordings it holds, so the reading is taken where the setup changes and
        stands through every report a run makes about it.
        """
        return stem_rows(self._state.gathering, mixes=self.mixes)

    def _action_label(self) -> str:
        """What the button says the run writes, read from the recordings taking part in it."""
        return self._messages.action_label(
            phase=self._run.phase,
            mixes=self.mixes,
            converted=playing_sources(self._state),
        )
