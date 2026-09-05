from pathlib import Path
from typing import Callable, List
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.logic.main.converter.logic import ConverterLogic
from sampletones_application.logic.main.converter.run import ConversionSuccess
from sampletones_application.services.conversion.result import ConversionResult
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.view_model.main.converter import (
    ACTIVE_PHASES,
    ConversionPhase,
    ConverterViewModel,
)
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.converter import GroupConversion
from tests.suite.language import FakeLanguageManager
from tests.unit.sampletones_application.logic.main.converter.texts import TEXTS

SCHEDULING: str = "sampletones_application.logic.main.converter.logic.CallbackQueue.add"
OUTPUT_PATH: str = "sampletones_application.logic.main.converter.destination.get_output_path"


def _config_writing_under(reconstructions_directory: Path) -> Config:
    """A configuration whose reconstructions are written under ``reconstructions_directory``."""
    config = Config()
    general = config.general.model_copy(update={"reconstructions_directory": str(reconstructions_directory)})
    return config.model_copy(update={"general": general})


@pytest.fixture
def session_manager(tmp_path: Path) -> SessionManager:
    """A session writing under the test's own directory, so the joining settings round-trip."""
    return SessionManager(UserProfile(config=tmp_path / "config.json", state=tmp_path / "state.yaml"))


@pytest.fixture
def service() -> MagicMock:
    """The conversion service the converter drives, which reports back through its subscription."""
    service = MagicMock()
    service.is_running.return_value = False
    return service


@pytest.fixture
def converter_logic(
    tmp_path: Path,
    session_manager: SessionManager,
    service: MagicMock,
) -> ConverterLogic:
    """A converter reading a real configuration, so resolving where a run writes answers as it does live.

    The configuration writes under the test's own directory, which keeps a target this converter
    resolves within the test rather than in the reconstructions the developer holds.
    """
    reconstructions_directory = tmp_path / "reconstructions"
    config_manager = MagicMock()
    config_manager.config = _config_writing_under(reconstructions_directory)
    config_manager.get_reconstructions_directory.return_value = reconstructions_directory
    scheduling = MagicMock(
        priorities=MagicMock(schedule=0),
        delays=MagicMock(schedule=0, cancel=0),
    )
    logic = ConverterLogic(
        config_manager,
        session_manager,
        service,
        scheduling=scheduling,
        language_manager=FakeLanguageManager(TEXTS),  # type: ignore[arg-type]
        is_operation_active=lambda: False,
    )
    logic.on_view_changed = MagicMock()
    logic.generate_library = MagicMock()
    logic.is_library_available = lambda: False
    return logic


def _view(converter_logic: ConverterLogic) -> ConverterViewModel:
    """The panel's last reading of the converter."""
    view_model: ConverterViewModel = converter_logic.on_view_changed.call_args.args[0]
    return view_model


def _phase(converter_logic: ConverterLogic) -> ConversionPhase:
    return _view(converter_logic).phase


def _reports(service: MagicMock, result: ConversionResult) -> None:
    """Hands the converter a result the conversion service would report to it."""
    handler: Callable[[ConversionResult], None] = service.subscribe.call_args.args[0]
    handler(result)


def _gathered(converter_logic: ConverterLogic, *names: str) -> None:
    converter_logic.set_stems_mode(True)
    converter_logic.add_sources([Path(f"/audio/{name}.wav") for name in names])


def _started_plan(converter_logic: ConverterLogic, service: MagicMock) -> GroupConversion:
    """The plan the converter hands the service once the library it waits for is ready."""
    converter_logic.is_library_available = lambda: True
    with patch(SCHEDULING):
        converter_logic.start_conversion(confirmed=True)

    plan: GroupConversion = service.start.call_args.args[1]
    return plan


class TestCancelDuringLibraryGeneration:
    """The converter requests a library when none exists and waits for it. Cancelling during that
    wait must abort the pending conversion and stop the in-flight generation."""

    def test_cancel_while_waiting_cancels_generation_and_finishes(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        cancel_generation = MagicMock()
        on_canceled = MagicMock()
        converter_logic.cancel_library_generation = cancel_generation
        converter_logic.on_canceled = on_canceled
        _aimed_at_a_recording(converter_logic, tmp_path)

        with patch(SCHEDULING):
            converter_logic.start_conversion()
            assert _phase(converter_logic) == ConversionPhase.WAITING

            converter_logic.cancel()

        cancel_generation.assert_called_once()
        on_canceled.assert_called_once()
        assert _phase(converter_logic) == ConversionPhase.CANCELED

    def test_wait_loop_aborts_once_no_longer_waiting(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
        tmp_path: Path,
    ) -> None:
        _aimed_at_a_recording(converter_logic, tmp_path)

        with patch(SCHEDULING) as scheduled:
            converter_logic.start_conversion()
            converter_logic.cancel()
            scheduled.reset_mock()

            converter_logic._wait_for_library_and_start()

        service.start.assert_not_called()
        scheduled.assert_not_called()

    def test_wait_poll_does_not_emit_a_zero_progress_view(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        """While waiting, the bar reflects the library-generation progress. A re-poll that finds the
        library still missing must only re-queue itself, never emit its own view: emitting one would
        carry ``progress=0.0`` and momentarily reset the bar."""
        _aimed_at_a_recording(converter_logic, tmp_path)

        with patch(SCHEDULING) as scheduled:
            converter_logic.start_conversion()
            converter_logic.on_view_changed.reset_mock()
            scheduled.reset_mock()

            converter_logic._wait_for_library_and_start()

        converter_logic.on_view_changed.assert_not_called()
        scheduled.assert_called_once()


class TestNoChannelsGuard:
    """With no channels enabled there is nothing to reconstruct, so the conversion must not start."""

    def test_no_generators_notifies_and_does_not_start(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.set_joining_channels(frozenset())
        on_no_generators = MagicMock()
        converter_logic.on_no_generators = on_no_generators

        converter_logic.start_conversion()

        on_no_generators.assert_called_once()
        converter_logic.generate_library.assert_not_called()
        assert _phase(converter_logic) == ConversionPhase.IDLE


class TestNothingToConvertGuard:
    """A converter aimed at nothing has no plan to run, so a request leaves it where it stands."""

    def test_a_request_with_nothing_picked_starts_nothing(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.emit_initial_view()

        converter_logic.start_conversion()

        converter_logic.generate_library.assert_not_called()
        assert _phase(converter_logic) == ConversionPhase.IDLE

    def test_a_mix_runs_without_a_recording_ever_being_picked(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        """A mix converts the recordings it gathered, so nothing about the browser's selection gates it."""
        _gathered(converter_logic, "a", "b")

        plan = _started_plan(converter_logic, service)

        assert plan.sources == (Path("/audio/a.wav"), Path("/audio/b.wav"))


class TestOverwriteGuard:
    """A single conversion writes one named file, so a run that would replace one asks first.

    A batch settles the question itself — it converts what is still to be written — so the
    prompt reaches the reader for the single-file and stems runs alone.
    """

    @staticmethod
    def _aimed_at(converter_logic: ConverterLogic, path: Path) -> Path:
        """Points the converter at ``path`` and answers where its run would write."""
        converter_logic.set_input_path(path)
        return _view(converter_logic).output_path

    @staticmethod
    def _standing(target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()

    def test_a_standing_target_is_put_to_the_reader_and_nothing_starts(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "song.wav"
        source.touch()
        target = self._aimed_at(converter_logic, source)
        self._standing(target)
        on_target_exists = MagicMock()
        converter_logic.on_target_exists = on_target_exists

        with patch(SCHEDULING):
            converter_logic.start_conversion()

        on_target_exists.assert_called_once_with(target)
        converter_logic.generate_library.assert_not_called()
        assert _phase(converter_logic) == ConversionPhase.IDLE

    def test_a_confirmed_run_goes_ahead(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "song.wav"
        source.touch()
        self._standing(self._aimed_at(converter_logic, source))
        on_target_exists = MagicMock()
        converter_logic.on_target_exists = on_target_exists

        with patch(SCHEDULING):
            converter_logic.start_conversion(confirmed=True)

        on_target_exists.assert_not_called()
        converter_logic.generate_library.assert_called_once()
        assert _phase(converter_logic) == ConversionPhase.WAITING

    def test_a_target_still_to_be_written_starts_straight_away(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "song.wav"
        source.touch()
        self._aimed_at(converter_logic, source)
        on_target_exists = MagicMock()
        converter_logic.on_target_exists = on_target_exists

        with patch(SCHEDULING):
            converter_logic.start_conversion()

        on_target_exists.assert_not_called()
        assert _phase(converter_logic) == ConversionPhase.WAITING

    def test_a_batch_starts_without_asking(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        """The scan keeps every reconstruction already written, so a standing file stops nothing."""
        sources = tmp_path / "sources"
        sources.mkdir()
        (sources / "song.wav").touch()
        converter_logic.set_input_path(sources)
        on_target_exists = MagicMock()
        converter_logic.on_target_exists = on_target_exists

        with patch(SCHEDULING):
            converter_logic.start_conversion()

        on_target_exists.assert_not_called()
        assert _phase(converter_logic) == ConversionPhase.WAITING


class TestStartConversionGate:
    """A conversion refuses to start while another exclusive operation is active, so two heavy
    processes cannot run at once."""

    def test_refuses_when_an_operation_is_active(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
        tmp_path: Path,
    ) -> None:
        _aimed_at_a_recording(converter_logic, tmp_path)
        converter_logic._is_operation_active = lambda: True

        converter_logic.start_conversion()

        service.start.assert_not_called()
        converter_logic.generate_library.assert_not_called()
        assert _phase(converter_logic) == ConversionPhase.IDLE

    def test_proceeds_when_nothing_is_active(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        _aimed_at_a_recording(converter_logic, tmp_path)

        with patch(SCHEDULING):
            converter_logic.start_conversion()

        converter_logic.generate_library.assert_called_once()
        assert _phase(converter_logic) == ConversionPhase.WAITING


class TestPickingWhatToConvert:
    """``get_output_path``'s contract is the ``OSError`` family: those failures abort the
    selection and report through ``on_error``; a failure outside the contract is a bug and
    propagates."""

    @pytest.mark.parametrize(
        "error",
        [FileNotFoundError("missing"), OSError("invalid path")],
        ids=["missing", "invalid"],
    )
    def test_path_failure_reports_error_and_aborts(
        self,
        converter_logic: ConverterLogic,
        error: Exception,
    ) -> None:
        converter_logic.on_error = MagicMock()

        with patch(OUTPUT_PATH, side_effect=error):
            converter_logic.set_input_path(Path("/tmp/input.wav"))

        converter_logic.on_error.assert_called_once_with(error)
        converter_logic.emit_initial_view()
        assert _view(converter_logic).input_path is None

    def test_unexpected_failure_propagates(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.on_error = MagicMock()

        with patch(OUTPUT_PATH, side_effect=KeyError("drive")), pytest.raises(KeyError):
            converter_logic.set_input_path(Path("/tmp/input.wav"))

        converter_logic.on_error.assert_not_called()

    def test_a_picked_recording_reaches_the_view(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        source = _aimed_at_a_recording(converter_logic, tmp_path)

        view_model = _view(converter_logic)

        assert (view_model.input_path, view_model.is_file) == (source, True)


class TestWhatACompletedConversionLeaves:
    """A completed conversion tells its listener what it wrote, so the follow-up offer can target
    the single reconstruction or the folder holding a batch."""

    def test_success_carries_the_reconstructions_that_were_written(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        on_success = MagicMock()
        converter_logic.on_success = on_success
        written = (Path("/reconstructions/kick.stn"),)

        _reports(service, ServiceSuccess(value=written))

        assert _phase(converter_logic) == ConversionPhase.COMPLETED
        on_success.assert_called_once_with(ConversionSuccess(written=written))

    def test_one_written_reconstruction_becomes_the_displayed_output(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        written = (Path("/reconstructions/kick.stn"),)

        _reports(service, ServiceSuccess(value=written))

        assert _view(converter_logic).output_path == written[0]

    def test_a_batch_loads_the_folder_and_one_file_loads_itself(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        converter_logic.on_load_file = MagicMock()
        converter_logic.on_load_directory = MagicMock()

        _reports(service, ServiceSuccess(value=(Path("/reconstructions/kick.stn"),)))
        converter_logic.handle_load_request()
        converter_logic.on_load_file.assert_called_once_with(Path("/reconstructions/kick.stn"))

        _reports(
            service,
            ServiceSuccess(value=(Path("/reconstructions/kick.stn"), Path("/reconstructions/snare.stn"))),
        )
        converter_logic.handle_load_request()
        converter_logic.on_load_directory.assert_called_once_with()


class TestFailureReturnsToIdle:
    """With no Close button, a failure reports through ``on_error`` and schedules its own return to
    idle so the panel never strands on the failed phase."""

    def test_failure_schedules_return_to_idle_and_reports(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        converter_logic.on_error = MagicMock()

        with patch(SCHEDULING) as scheduled:
            _reports(service, ServiceError(exception=RuntimeError("boom")))

        assert _phase(converter_logic) == ConversionPhase.FAILED
        scheduled.assert_called_once()
        assert scheduled.call_args.args[0] == converter_logic.close
        converter_logic.on_error.assert_called_once()


class TestActivePhases:
    """``is_active`` reports a conversion occupying resources for every non-idle, non-terminal phase —
    covering the WAITING preparation that runs before the service starts."""

    def test_a_requested_conversion_is_active_before_the_service_takes_it(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        _aimed_at_a_recording(converter_logic, tmp_path)

        with patch(SCHEDULING):
            converter_logic.start_conversion()

        assert _phase(converter_logic) in ACTIVE_PHASES
        assert converter_logic.is_active is True

    def test_a_settled_conversion_holds_nothing(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _reports(service, ServiceSuccess(value=(Path("/reconstructions/kick.stn"),)))

        assert converter_logic.is_active is False

    def test_a_converter_that_has_run_nothing_is_idle(self, converter_logic: ConverterLogic) -> None:
        converter_logic.emit_initial_view()

        assert (_phase(converter_logic), converter_logic.is_active) == (ConversionPhase.IDLE, False)


class TestGatheringRecordings:
    """The rows a reader gathers, as the panel reads them back."""

    def _names(self, converter_logic: ConverterLogic) -> List[str]:
        return [row.name for row in _view(converter_logic).stem_sources]

    def test_selecting_a_recording_in_stems_mode_adds_it(self, converter_logic: ConverterLogic) -> None:
        converter_logic.set_stems_mode(True)

        converter_logic.select_source(Path("/audio/bass.wav"))
        converter_logic.select_source(Path("/audio/lead.wav"))

        assert self._names(converter_logic) == ["bass", "lead"]

    def test_adding_a_listed_recording_leaves_the_list_as_it_is(self, converter_logic: ConverterLogic) -> None:
        _gathered(converter_logic, "bass", "lead")
        converter_logic.isolate_source(Path("/audio/lead.wav"))

        converter_logic.add_sources([Path("/audio/lead.wav")])

        rows = _view(converter_logic).stem_sources
        assert [row.name for row in rows] == ["bass", "lead"]
        assert [row.level for row in rows] == [0, 1]

    def test_the_list_stops_at_the_room_it_has(self, converter_logic: ConverterLogic) -> None:
        _gathered(converter_logic, *[str(index) for index in range(MAX_STEM_SOURCES + 3)])

        assert converter_logic.source_count == MAX_STEM_SOURCES
        assert converter_logic.room_for_sources == 0

    def test_removing_a_recording_takes_it_out(self, converter_logic: ConverterLogic) -> None:
        _gathered(converter_logic, "a", "b")

        converter_logic.remove_source(Path("/audio/a.wav"))

        assert self._names(converter_logic) == ["b"]

    def test_entering_stems_mode_carries_the_picked_file_in(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        source = _aimed_at_a_recording(converter_logic, tmp_path)

        converter_logic.set_stems_mode(True)

        assert self._names(converter_logic) == [source.stem]

    def test_leaving_stems_mode_keeps_the_recording_that_picks_first(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        _gathered(converter_logic, "a", "b")

        converter_logic.set_stems_mode(False)

        assert converter_logic.source_count == 1

    def test_a_row_reports_the_level_it_landed_on(self, converter_logic: ConverterLogic) -> None:
        _gathered(converter_logic, "a", "b")

        converter_logic.move_source_to_new_level(Path("/audio/b.wav"), 0)

        rows = _view(converter_logic).stem_sources
        assert [(row.path.name, row.level, row.level_count) for row in rows] == [
            ("b.wav", 0, 2),
            ("a.wav", 1, 2),
        ]


class TestWhatTheGatheredRecordingsRun:
    """What the converter asks the service to run, once a reader has set the mix up."""

    def test_the_rows_channels_and_levels_reach_the_setup(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _gathered(converter_logic, "a", "b")
        converter_logic.set_source_channels(Path("/audio/a.wav"), frozenset({ChannelName.PULSE1}))
        converter_logic.isolate_source(Path("/audio/b.wav"))

        plan = _started_plan(converter_logic, service)

        assert plan.stems.entries[0].settings.channels == [ChannelName.PULSE1]
        assert plan.stems.hierarchy.levels == [[0], [1]]

    def test_a_recording_left_with_no_channel_takes_no_part(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _gathered(converter_logic, "a", "b")

        converter_logic.set_source_channels(Path("/audio/a.wav"), frozenset())
        plan = _started_plan(converter_logic, service)

        assert converter_logic.source_count == 2
        assert plan.sources == (Path("/audio/b.wav"),)
        assert [entry.id for entry in plan.stems.entries] == [0]

    def test_the_hierarchy_mode_reaches_the_setup(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _gathered(converter_logic, "a")

        converter_logic.set_hierarchy_mode(HierarchyMode.STRICT)

        assert _started_plan(converter_logic, service).stems.hierarchy.mode == HierarchyMode.STRICT

    def test_the_cap_the_reader_asked_for_reaches_the_setup(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _gathered(converter_logic, "a")

        converter_logic.set_channel_cap(1)

        assert _started_plan(converter_logic, service).stems.channel_cap == 1

    def test_the_configuration_reaches_the_service_with_the_plan(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _gathered(converter_logic, "a")

        _started_plan(converter_logic, service)

        started_config = service.start.call_args.args[0]
        assert started_config == converter_logic._config_manager.config


class TestTheStemsView:
    """What the panel is told about the setup being built."""

    def test_the_rows_reach_the_view_in_list_order(self, converter_logic: ConverterLogic) -> None:
        _gathered(converter_logic, "a", "b")

        view_model = _view(converter_logic)

        assert [row.name for row in view_model.stem_sources] == ["a", "b"]
        assert view_model.stems_mode is True
        assert view_model.has_input is True

    def test_a_row_shows_the_channels_it_may_take(self, converter_logic: ConverterLogic) -> None:
        _gathered(converter_logic, "a")

        converter_logic.set_source_channels(Path("/audio/a.wav"), frozenset({ChannelName.NOISE}))

        assert _view(converter_logic).stem_sources[0].channels == frozenset({ChannelName.NOISE})

    def test_the_view_states_whether_another_recording_fits(self, converter_logic: ConverterLogic) -> None:
        _gathered(converter_logic, *[str(index) for index in range(MAX_STEM_SOURCES)])

        view_model = _view(converter_logic)

        assert view_model.source_count == MAX_STEM_SOURCES
        assert view_model.can_add_source is False

    def test_an_empty_stems_list_offers_nothing_to_convert(self, converter_logic: ConverterLogic) -> None:
        converter_logic.set_stems_mode(True)

        view_model = _view(converter_logic)

        assert view_model.has_input is False
        assert view_model.convert_button_enabled is False

    def test_the_cap_the_view_reports_holds_within_the_channels_enabled(
        self,
        converter_logic: ConverterLogic,
        session_manager: SessionManager,
    ) -> None:
        channels = session_manager.converter_settings.channels

        converter_logic.set_channel_cap(len(channels) + 5)

        assert _view(converter_logic).channel_cap == len(channels)


def _aimed_at_a_recording(converter_logic: ConverterLogic, tmp_path: Path) -> Path:
    """Points the converter at a recording standing on disk, the way the browser does."""
    source = tmp_path / "song.wav"
    source.touch()
    converter_logic.set_input_path(source)
    return source
