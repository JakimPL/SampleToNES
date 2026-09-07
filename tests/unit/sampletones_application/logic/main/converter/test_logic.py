from pathlib import Path
from typing import Callable, List
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.constants.output import OutputKind
from sampletones_application.constants.sources import SourceKind
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
from sampletones_core.reconstructions.converter.paths import get_audio_files
from tests.suite.base import BaseTestSuite
from tests.suite.language import FakeLanguageManager
from tests.unit.sampletones_application.logic.main.converter.texts import TEXTS

SCHEDULING: str = "sampletones_application.logic.main.converter.logic.CallbackQueue.add"


def _config_writing_under(reconstructions_directory: Path) -> Config:
    """A configuration whose reconstructions are written under ``reconstructions_directory``."""
    config = Config()
    general = config.general.model_copy(update={"reconstructions_directory": str(reconstructions_directory)})
    return config.model_copy(update={"general": general})


def _config_manager_writing_under(reconstructions_directory: Path) -> MagicMock:
    """The configuration manager a converter reads where a run writes from."""
    config_manager = MagicMock()
    config_manager.config = _config_writing_under(reconstructions_directory)
    config_manager.get_reconstructions_directory.return_value = reconstructions_directory
    return config_manager


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
    config_manager = _config_manager_writing_under(reconstructions_directory)
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


def _mixing(converter_logic: ConverterLogic, *names: str) -> None:
    """Gathers recordings into a mix, which is the run several recordings amount to."""
    converter_logic.set_output(OutputKind.MIXED)
    converter_logic.gather_recordings([Path(f"/audio/{name}.wav") for name in names])


def _listed(converter_logic: ConverterLogic, *names: str) -> None:
    """Gathers recordings into a run writing one reconstruction apiece."""
    converter_logic.gather_recordings([Path(f"/audio/{name}.wav") for name in names])


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
    """A gathered recording holding no channel reconstructs nothing, so the run must not start."""

    def test_no_generators_notifies_and_does_not_start(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.set_joining_channels(frozenset())
        _listed(converter_logic, "a")
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
        _mixing(converter_logic, "a", "b")

        plan = _started_plan(converter_logic, service)

        assert plan.sources == (Path("/audio/a.wav"), Path("/audio/b.wav"))


class TestOverwriteGuard:
    """A single conversion writes one named file, so a run that would replace one asks first.

    A batch settles the question itself — it converts what is still to be written — so the
    prompt reaches the reader for the single-file and stems runs alone.
    """

    @staticmethod
    def _aimed_at(converter_logic: ConverterLogic, path: Path) -> Path:
        """Gathers ``path`` and answers where its run would write."""
        converter_logic.gather_recordings([path])
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

        on_target_exists.assert_called_once_with((target,))
        converter_logic.generate_library.assert_not_called()
        assert _phase(converter_logic) == ConversionPhase.IDLE

    def _target_alone(self, converter_logic: ConverterLogic, source: Path) -> Path:
        """Where a run over this recording alone would write, leaving the setup as it was found."""
        target = self._aimed_at(converter_logic, source)
        converter_logic.remove_source(source)
        return target

    def test_every_standing_target_is_named_to_the_reader(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        """A recording the reader named is written whenever the run goes, so all of them are named.

        The answer covers each one it is given, which is what makes the prompt worth reading.
        """
        sources = []
        targets = []
        for name in ("one.wav", "two.wav", "three.wav"):
            source = tmp_path / name
            source.touch()
            sources.append(source)
            targets.append(self._target_alone(converter_logic, source))

        for target in targets:
            self._standing(target)

        converter_logic.gather_recordings(sources)
        on_target_exists = MagicMock()
        converter_logic.on_target_exists = on_target_exists

        with patch(SCHEDULING):
            converter_logic.start_conversion()

        on_target_exists.assert_called_once_with(tuple(targets))
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

    def test_a_folder_starts_without_asking(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        """A recording gathered from a folder is never written over, so a standing file stops nothing."""
        sources = tmp_path / "sources"
        sources.mkdir()
        (sources / "song.wav").touch()
        converter_logic.gather_folder(sources, get_audio_files(sources, sort=True))
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


class TestWhatTheSetupNamesItselfBy:
    """A setup holding one row is that row, which is what a reader converting one file reads."""

    def test_one_recording_names_itself(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        source = _aimed_at_a_recording(converter_logic, tmp_path)

        view_model = _view(converter_logic)

        assert (view_model.input_path, view_model.is_file) == (source, True)

    def test_one_folder_names_the_tree_it_mirrors(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        sources = tmp_path / "sources"
        sources.mkdir()
        (sources / "song.wav").touch()

        converter_logic.gather_folder(sources, get_audio_files(sources, sort=True))

        view_model = _view(converter_logic)
        assert (view_model.input_path, view_model.is_file) == (sources, False)

    def test_several_rows_name_none_of_them(self, converter_logic: ConverterLogic) -> None:
        _listed(converter_logic, "a", "b")

        assert _view(converter_logic).input_path is None


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

    def test_a_gathered_recording_becomes_a_row(self, converter_logic: ConverterLogic) -> None:
        converter_logic.gather_recordings([Path("/audio/bass.wav")])
        converter_logic.gather_recordings([Path("/audio/lead.wav")])

        assert self._names(converter_logic) == ["bass", "lead"]

    def test_adding_a_listed_recording_leaves_the_list_as_it_is(self, converter_logic: ConverterLogic) -> None:
        _mixing(converter_logic, "bass", "lead")
        converter_logic.isolate_source(Path("/audio/lead.wav"))

        converter_logic.gather_recordings([Path("/audio/lead.wav")])

        rows = _view(converter_logic).stem_sources
        assert [row.name for row in rows] == ["bass", "lead"]
        assert [row.level for row in rows] == [0, 1]

    def test_the_list_stops_at_the_room_it_has(self, converter_logic: ConverterLogic) -> None:
        _mixing(converter_logic, *[str(index) for index in range(MAX_STEM_SOURCES + 3)])

        assert converter_logic.source_count == MAX_STEM_SOURCES
        assert converter_logic.room_for_sources == 0

    def test_removing_a_recording_takes_it_out(self, converter_logic: ConverterLogic) -> None:
        _mixing(converter_logic, "a", "b")

        converter_logic.remove_source(Path("/audio/a.wav"))

        assert self._names(converter_logic) == ["b"]

    def test_turning_to_a_mix_carries_the_picked_file_in(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        source = _aimed_at_a_recording(converter_logic, tmp_path)

        converter_logic.set_output(OutputKind.MIXED)

        assert self._names(converter_logic) == [source.stem]

    def test_turning_away_from_a_mix_keeps_every_recording(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        _mixing(converter_logic, "a", "b")

        converter_logic.set_output(OutputKind.PER_RECORDING)

        assert converter_logic.source_count == 2

    def test_a_per_recording_run_takes_more_than_a_mix_could_hold(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        _listed(converter_logic, *[str(index) for index in range(MAX_STEM_SOURCES + 3)])

        assert converter_logic.source_count == MAX_STEM_SOURCES + 3

    def test_a_row_reports_the_level_it_landed_on(self, converter_logic: ConverterLogic) -> None:
        _mixing(converter_logic, "a", "b")

        converter_logic.move_source_to_new_level(Path("/audio/b.wav"), 0)

        rows = _view(converter_logic).stem_sources
        assert [(row.path.name, row.level, row.level_count) for row in rows] == [
            ("b.wav", 0, 2),
            ("a.wav", 1, 2),
        ]


class TestAnsweringWhichRecordingsToMix:
    """A mix reaching a fixed number of recordings is put to the reader, and the answer is what
    the mix is then built from: what it names joins, and what it leaves out goes."""

    def _names(self, converter_logic: ConverterLogic) -> List[str]:
        return [row.name for row in _view(converter_logic).stem_sources]

    def test_the_answer_names_the_whole_mix(self, converter_logic: ConverterLogic) -> None:
        _mixing(converter_logic, "a", "b", "c")

        converter_logic.mix_only([Path("/audio/a.wav"), Path("/audio/c.wav")])

        assert self._names(converter_logic) == ["a", "c"]

    def test_a_recording_the_list_never_held_joins_it(self, converter_logic: ConverterLogic) -> None:
        """A full mix is answered by letting one go for one a folder offered, in the one gesture."""
        _mixing(converter_logic, *[str(index) for index in range(MAX_STEM_SOURCES)])

        standing = [Path(f"/audio/{index}.wav") for index in range(MAX_STEM_SOURCES - 1)]
        converter_logic.mix_only([*standing, Path("/audio/late.wav")])

        assert self._names(converter_logic)[-1] == "late"
        assert converter_logic.source_count == MAX_STEM_SOURCES

    def test_a_recording_standing_keeps_the_channels_it_was_given(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        _mixing(converter_logic, "a", "b")
        converter_logic.set_source_channels(Path("/audio/a.wav"), frozenset({ChannelName.NOISE}))

        converter_logic.mix_only([Path("/audio/a.wav")])

        assert _view(converter_logic).stem_sources[0].channels == frozenset({ChannelName.NOISE})

    def test_the_run_it_leaves_is_a_mix(self, converter_logic: ConverterLogic) -> None:
        _listed(converter_logic, "a", "b")

        converter_logic.mix_only([Path("/audio/a.wav")])

        assert converter_logic.mixes


class TestWhatTheGatheredRecordingsRun:
    """What the converter asks the service to run, once a reader has set the mix up."""

    def test_the_rows_channels_and_levels_reach_the_setup(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _mixing(converter_logic, "a", "b")
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
        _mixing(converter_logic, "a", "b")

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
        _mixing(converter_logic, "a")

        converter_logic.set_hierarchy_mode(HierarchyMode.STRICT)

        assert _started_plan(converter_logic, service).stems.hierarchy.mode == HierarchyMode.STRICT

    def test_the_cap_the_reader_asked_for_reaches_the_setup(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _mixing(converter_logic, "a")

        converter_logic.set_channel_cap(1)

        assert _started_plan(converter_logic, service).stems.channel_cap == 1

    def test_the_configuration_reaches_the_service_with_the_plan(
        self,
        converter_logic: ConverterLogic,
        service: MagicMock,
    ) -> None:
        _mixing(converter_logic, "a")

        _started_plan(converter_logic, service)

        started_config = service.start.call_args.args[0]
        assert started_config == converter_logic._config_manager.config


class TestAFolderInTheList:
    """A folder stands as one row, answering for every recording gathered below it."""

    def _folder(self, converter_logic: ConverterLogic, tmp_path: Path, names: List[str]) -> Path:
        root = tmp_path / "sources"
        root.mkdir()
        for name in names:
            (root / name).touch()

        converter_logic.gather_folder(root, get_audio_files(root, sort=True))
        return root

    def test_a_folder_draws_one_row_naming_what_it_holds(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        root = self._folder(converter_logic, tmp_path, ["a.wav", "b.wav"])

        rows = _view(converter_logic).stem_sources

        assert len(rows) == 1
        assert (rows[0].path, rows[0].holds, rows[0].stands_for_a_folder) == (root, 2, True)

    def test_a_folder_its_recordings_agree_on_reads_as_held(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        """The list and the settings card read one folder the same way, since both fold its rows."""
        root = self._folder(converter_logic, tmp_path, ["a.wav", "b.wav"])
        converter_logic.select_row(root, SourceKind.FOLDER)

        row = _view(converter_logic).stem_sources[0]

        assert row.channels == converter_logic.settings_slots[0].held_channels
        assert row.partial_channels == frozenset()

    def test_a_folder_its_recordings_differ_on_reads_as_half_held(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        root = self._folder(converter_logic, tmp_path, ["a.wav", "b.wav"])

        converter_logic.set_source_channels(root / "a.wav", frozenset({ChannelName.PULSE1}))

        row = _view(converter_logic).stem_sources[0]
        assert row.channels == frozenset({ChannelName.PULSE1})
        assert ChannelName.TRIANGLE in row.partial_channels

    def test_one_gesture_settles_the_whole_folder(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        root = self._folder(converter_logic, tmp_path, ["a.wav", "b.wav"])
        converter_logic.set_source_channels(root / "a.wav", frozenset({ChannelName.PULSE1}))

        converter_logic.toggle_folder_channel(root, ChannelName.TRIANGLE)

        row = _view(converter_logic).stem_sources[0]
        assert ChannelName.TRIANGLE in row.channels
        assert ChannelName.TRIANGLE not in row.partial_channels

    def test_a_folder_every_recording_of_which_holds_it_lets_it_go(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        root = self._folder(converter_logic, tmp_path, ["a.wav", "b.wav"])

        converter_logic.toggle_folder_channel(root, ChannelName.TRIANGLE)

        row = _view(converter_logic).stem_sources[0]
        assert ChannelName.TRIANGLE not in row.channels
        assert ChannelName.TRIANGLE not in row.partial_channels

    def test_removing_a_folder_takes_everything_it_holds(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        root = self._folder(converter_logic, tmp_path, ["a.wav", "b.wav"])

        converter_logic.remove_folder(root)

        assert _view(converter_logic).stem_sources == ()
        assert converter_logic.source_count == 0

    def test_turning_to_a_mix_gives_up_the_folder(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        self._folder(converter_logic, tmp_path, ["a.wav", "b.wav"])

        converter_logic.set_output(OutputKind.MIXED)

        rows = _view(converter_logic).stem_sources
        assert [row.stands_for_a_folder for row in rows] == [False, False]


class TestTheStemsView:
    """What the panel is told about the setup being built."""

    def test_the_rows_reach_the_view_in_list_order(self, converter_logic: ConverterLogic) -> None:
        _mixing(converter_logic, "a", "b")

        view_model = _view(converter_logic)

        assert [row.name for row in view_model.stem_sources] == ["a", "b"]
        assert view_model.mixes is True
        assert view_model.has_input is True

    def test_a_row_shows_the_channels_it_may_take(self, converter_logic: ConverterLogic) -> None:
        _mixing(converter_logic, "a")

        converter_logic.set_source_channels(Path("/audio/a.wav"), frozenset({ChannelName.NOISE}))

        assert _view(converter_logic).stem_sources[0].channels == frozenset({ChannelName.NOISE})

    def test_the_view_states_whether_another_recording_fits(self, converter_logic: ConverterLogic) -> None:
        _mixing(converter_logic, *[str(index) for index in range(MAX_STEM_SOURCES)])

        view_model = _view(converter_logic)

        assert view_model.source_count == MAX_STEM_SOURCES
        assert view_model.can_add_source is False

    def test_an_empty_stems_list_offers_nothing_to_convert(self, converter_logic: ConverterLogic) -> None:
        converter_logic.set_output(OutputKind.MIXED)

        view_model = _view(converter_logic)

        assert view_model.has_input is False
        assert view_model.convert_button_enabled is False

    def test_the_cap_the_view_reports_holds_within_the_channels_there_are(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.set_channel_cap(len(ChannelName) + 5)

        assert _view(converter_logic).channel_cap == len(ChannelName)


def _aimed_at_a_recording(converter_logic: ConverterLogic, tmp_path: Path) -> Path:
    """Gathers a recording standing on disk, the way a click in the browser does."""
    source = tmp_path / "song.wav"
    source.touch()
    converter_logic.gather_recordings([source])
    return source


class TestAFolderOfFolders(BaseTestSuite):
    """A gathered folder stands for every recording below it, however deep the tree goes."""

    @staticmethod
    def _tree(tmp_path: Path) -> Path:
        root = tmp_path / "library"
        nested = root / "loops" / "drums"
        nested.mkdir(parents=True)
        (root / "top.wav").touch()
        (nested / "deep.wav").touch()
        (nested / "notes.txt").write_text("not audio")
        return root

    def test_every_recording_below_it_is_gathered(
        self,
        converter_logic: ConverterLogic,
        tmp_path: Path,
    ) -> None:
        root = self._tree(tmp_path)

        converter_logic.gather_folder(root, get_audio_files(root, sort=True))

        assert {path.name for path in converter_logic.gathered_paths} == {"top.wav", "deep.wav"}

    def test_it_still_stands_as_one_row(self, converter_logic: ConverterLogic, tmp_path: Path) -> None:
        root = self._tree(tmp_path)

        converter_logic.gather_folder(root, get_audio_files(root, sort=True))

        rows = _view(converter_logic).stem_sources
        assert len(rows) == 1
        assert (rows[0].path, rows[0].holds) == (root, 2)


class TestTheRunTheSessionCarries(BaseTestSuite):
    """The shape of a run is carried between launches, so the converter opens where it was left."""

    def test_the_output_switch_is_written_down(
        self,
        converter_logic: ConverterLogic,
        session_manager: SessionManager,
    ) -> None:
        converter_logic.set_output(OutputKind.MIXED)

        assert session_manager.converter_output is OutputKind.MIXED

    def test_the_channel_cap_is_written_down(
        self,
        converter_logic: ConverterLogic,
        session_manager: SessionManager,
    ) -> None:
        converter_logic.set_channel_cap(2)

        assert session_manager.converter_channel_cap == 2

    def test_the_order_is_written_down(
        self,
        converter_logic: ConverterLogic,
        session_manager: SessionManager,
    ) -> None:
        converter_logic.set_hierarchy_mode(HierarchyMode.STRICT)

        assert session_manager.converter_hierarchy_mode is HierarchyMode.STRICT

    def test_a_converter_opens_on_what_the_session_carries(
        self,
        converter_logic: ConverterLogic,
        session_manager: SessionManager,
        service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """The whole point of writing them down: the next launch reads them back."""
        converter_logic.set_output(OutputKind.MIXED)
        converter_logic.set_channel_cap(2)
        converter_logic.set_hierarchy_mode(HierarchyMode.STRICT)

        reopened = ConverterLogic(
            _config_manager_writing_under(tmp_path / "reconstructions"),
            session_manager,
            service,
            scheduling=MagicMock(priorities=MagicMock(schedule=0), delays=MagicMock(schedule=0, cancel=0)),
            language_manager=FakeLanguageManager(TEXTS),  # type: ignore[arg-type]
            is_operation_active=lambda: False,
        )

        assert reopened.mixes is True
