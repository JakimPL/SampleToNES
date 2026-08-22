from pathlib import Path
from typing import Dict, Final
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.constants.conversion import MAX_STEM_SOURCES, MIN_CHANNEL_CAP
from sampletones_application.logic.main.converter import (
    ConversionSuccess,
    ConverterLogic,
)
from sampletones_application.services.result import ServiceProgress
from sampletones_application.view_model.main.converter import (
    ACTIVE_PHASES,
    ConversionPhase,
    ConverterViewModel,
)
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.converter import DirectoryConversion, GroupConversion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from tests.suite.language import FakeLanguageManager

TEXTS: Final[Dict[str, str]] = {
    "main.converter.label.convert_sample_button": "Convert sample",
    "main.converter.label.convert_directory_button": "Convert directory",
    "main.converter.label.cancel_button": "Cancel",
    "main.converter.template.convert_label_template": "{}: {}",
    "main.converter.template.progress_template": "Progress: {}/{} files",
    "main.converter.template.single_progress_template": "Reconstructing {}...",
    "global.dialog.template.time_estimation": "",
}


def _config_writing_under(reconstructions_directory: Path) -> Config:
    """A configuration whose reconstructions are written under ``reconstructions_directory``."""
    config = Config()
    general = config.general.model_copy(update={"reconstructions_directory": str(reconstructions_directory)})
    return config.model_copy(update={"general": general})


@pytest.fixture
def converter_logic(tmp_path: Path) -> ConverterLogic:
    """A converter reading a real configuration, so resolving where a run writes answers as it does live.

    The configuration writes under the test's own directory, which keeps a target this converter
    resolves within the test rather than in the reconstructions the developer holds.
    """
    reconstructions_directory = tmp_path / "reconstructions"
    config_manager = MagicMock()
    config_manager.config = _config_writing_under(reconstructions_directory)
    config_manager.get_reconstructions_directory.return_value = reconstructions_directory
    service = MagicMock()
    service.is_running.return_value = False
    scheduling = MagicMock(
        priorities=MagicMock(schedule=0),
        delays=MagicMock(schedule=0, cancel=0),
    )
    logic = ConverterLogic(
        config_manager,
        service,
        scheduling=scheduling,
        language_manager=FakeLanguageManager(TEXTS),  # type: ignore[arg-type]
        is_operation_active=lambda: False,
    )
    logic.on_view_changed = MagicMock()
    logic.generate_library = MagicMock()
    logic.is_library_available = lambda: False
    return logic


class TestCancelDuringLibraryGeneration:
    """The converter requests a library when none exists and waits for it. Cancelling during that
    wait must abort the pending conversion and stop the in-flight generation."""

    def test_cancel_while_waiting_cancels_generation_and_finishes(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        cancel_generation = MagicMock()
        on_cancelled = MagicMock()
        converter_logic.cancel_library_generation = cancel_generation
        converter_logic.on_cancelled = on_cancelled

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()
            assert converter_logic._phase == ConversionPhase.WAITING

            converter_logic.cancel()

        cancel_generation.assert_called_once()
        on_cancelled.assert_called_once()
        assert converter_logic._phase == ConversionPhase.CANCELLED

    def test_wait_loop_aborts_once_no_longer_waiting(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        with patch("sampletones_application.logic.main.converter.CallbackQueue.add") as scheduled:
            converter_logic.start_conversion()
            converter_logic.cancel()
            scheduled.reset_mock()

            converter_logic._wait_for_library_and_start()

        converter_logic._service.start.assert_not_called()
        scheduled.assert_not_called()

    def test_wait_poll_does_not_emit_a_zero_progress_view(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        """While waiting, the bar reflects the library-generation progress. A re-poll that finds the
        library still missing must only re-queue itself, never emit its own view: emitting one would
        carry ``progress=0.0`` and momentarily reset the bar."""
        with patch("sampletones_application.logic.main.converter.CallbackQueue.add") as scheduled:
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
        config = converter_logic._config_manager.config
        converter_logic._config_manager.config = config.model_copy(
            update={"generation": config.generation.model_copy(update={"channels": []})}
        )
        on_no_generators = MagicMock()
        converter_logic.on_no_generators = on_no_generators

        converter_logic.start_conversion()

        on_no_generators.assert_called_once()
        converter_logic.generate_library.assert_not_called()
        assert converter_logic._phase == ConversionPhase.IDLE


class TestOverwriteGuard:
    """A single conversion writes one named file, so a run that would replace one asks first.

    A batch settles the question itself — it converts what is still to be written — so the
    prompt reaches the reader for the single-file and stems runs alone.
    """

    @staticmethod
    def _aimed_at(converter_logic: ConverterLogic, path: Path) -> Path:
        """Points the converter at ``path`` and answers where its run would write."""
        converter_logic.set_input_path(path)
        config = converter_logic._config_manager.config
        return GroupConversion(sources=(path,), stems=StemsConfig()).jobs(config)[0].output_path

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

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()

        on_target_exists.assert_called_once_with(target)
        converter_logic.generate_library.assert_not_called()
        assert converter_logic._phase == ConversionPhase.IDLE

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

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion(confirmed=True)

        on_target_exists.assert_not_called()
        converter_logic.generate_library.assert_called_once()
        assert converter_logic._phase == ConversionPhase.WAITING

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

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()

        on_target_exists.assert_not_called()
        assert converter_logic._phase == ConversionPhase.WAITING

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

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()

        on_target_exists.assert_not_called()
        assert converter_logic._phase == ConversionPhase.WAITING


class TestActivePhases:
    """``is_active`` reports a conversion occupying resources for every non-idle, non-terminal phase —
    covering the WAITING preparation that runs before the service starts."""

    @pytest.mark.parametrize("phase", sorted(ACTIVE_PHASES, key=str))
    def test_active_during_non_terminal_phases(
        self,
        converter_logic: ConverterLogic,
        phase: ConversionPhase,
    ) -> None:
        converter_logic._phase = phase
        assert converter_logic.is_active is True

    @pytest.mark.parametrize(
        "phase",
        [
            ConversionPhase.IDLE,
            ConversionPhase.COMPLETED,
            ConversionPhase.CANCELLED,
            ConversionPhase.FAILED,
        ],
    )
    def test_inactive_when_idle_or_terminal(
        self,
        converter_logic: ConverterLogic,
        phase: ConversionPhase,
    ) -> None:
        converter_logic._phase = phase
        assert converter_logic.is_active is False


def _last_view_model(converter_logic: ConverterLogic) -> ConverterViewModel:
    return converter_logic.on_view_changed.call_args.args[0]


class TestActionLabel:
    """The one action button's label is a projection of converter state, composed where the display
    strings are resolved (the logic layer) rather than glued together in the panel: it names the
    selected input while idle and reads the cancel label once a conversion holds resources.
    """

    def test_idle_file_label_names_the_selected_file(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._is_file = True
        converter_logic._input_path = Path("/audio/kick.wav")

        converter_logic.emit_initial_view()

        assert _last_view_model(converter_logic).action_label == "Convert sample: kick.wav"

    def test_idle_directory_label_uses_the_directory_variant(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._is_file = False
        converter_logic._input_path = Path("/audio/drums")

        converter_logic.emit_initial_view()

        assert _last_view_model(converter_logic).action_label == "Convert directory: drums"

    def test_idle_without_input_reads_the_bare_convert_label(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._input_path = None

        converter_logic.emit_initial_view()

        assert _last_view_model(converter_logic).action_label == "Convert sample"

    def test_active_conversion_reads_the_cancel_label(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._input_path = Path("/audio/kick.wav")

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()

        assert _last_view_model(converter_logic).action_label == "Cancel"


class TestStartConversionGate:
    """A conversion refuses to start while another exclusive operation is active, so two heavy
    processes cannot run at once."""

    def test_refuses_when_an_operation_is_active(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._is_operation_active = lambda: True

        converter_logic.start_conversion()

        converter_logic._service.start.assert_not_called()
        converter_logic.generate_library.assert_not_called()
        assert converter_logic._phase == ConversionPhase.IDLE

    def test_proceeds_when_nothing_is_active(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()

        converter_logic.generate_library.assert_called_once()
        assert converter_logic._phase == ConversionPhase.WAITING


class TestAssignPaths:
    """``get_output_path``'s contract is the ``OSError`` family: those failures abort the
    conversion and report through ``on_error``; a failure outside the contract is a bug and
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

        with patch(
            "sampletones_application.logic.main.converter.get_output_path",
            side_effect=error,
        ):
            result = converter_logic._assign_paths(
                Path("/tmp/input.wav"),
                MagicMock(),
            )

        assert result is False
        converter_logic.on_error.assert_called_once_with(error)

    def test_unexpected_failure_propagates(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.on_error = MagicMock()

        with (
            patch(
                "sampletones_application.logic.main.converter.get_output_path",
                side_effect=KeyError("drive"),
            ),
            pytest.raises(KeyError),
        ):
            converter_logic._assign_paths(Path("/tmp/input.wav"), MagicMock())

        converter_logic.on_error.assert_not_called()


class TestConversionCompleteHandsOverOutcome:
    """A completed conversion tells its listener what it wrote, so the follow-up offer can target
    the single reconstruction or the folder holding a batch."""

    def test_success_carries_the_reconstructions_that_were_written(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        on_success = MagicMock()
        converter_logic.on_success = on_success
        written = (Path("/reconstructions/kick.rcn"),)

        converter_logic._on_conversion_complete(written)

        assert converter_logic._phase == ConversionPhase.COMPLETED
        on_success.assert_called_once_with(ConversionSuccess(written=written))

    def test_one_written_reconstruction_becomes_the_displayed_output(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        written = (Path("/reconstructions/kick.rcn"),)

        converter_logic._on_conversion_complete(written)

        assert converter_logic._output_path == written[0]

    def test_a_batch_loads_the_folder_and_one_file_loads_itself(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.on_load_file = MagicMock()
        converter_logic.on_load_directory = MagicMock()

        converter_logic._on_conversion_complete((Path("/reconstructions/kick.rcn"),))
        converter_logic.handle_load_request()
        converter_logic.on_load_file.assert_called_once_with(Path("/reconstructions/kick.rcn"))

        converter_logic._on_conversion_complete((Path("/reconstructions/kick.rcn"), Path("/reconstructions/snare.rcn")))
        converter_logic.handle_load_request()
        converter_logic.on_load_directory.assert_called_once_with()


class TestFailureReturnsToIdle:
    """With no Close button, a failure reports through ``on_error`` and schedules its own return to
    idle so the panel never strands on the failed phase."""

    def test_failure_schedules_return_to_idle_and_reports(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.on_error = MagicMock()

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add") as scheduled:
            converter_logic._on_conversion_error(RuntimeError("boom"))

        assert converter_logic._phase == ConversionPhase.FAILED
        scheduled.assert_called_once()
        assert scheduled.call_args.args[0] == converter_logic.close
        converter_logic.on_error.assert_called_once()


class TestConversionPlan:
    """What the converter asks the service to run: one reconstruction for a file, one per audio
    file for a directory."""

    def _prepare(self, converter_logic: ConverterLogic, input_path: Path, is_file: bool) -> Config:
        config = Config()
        converter_logic._config_manager.config = config
        converter_logic._input_path = input_path
        converter_logic._is_file = is_file
        return config

    def test_a_file_becomes_one_group_over_that_file(self, converter_logic: ConverterLogic) -> None:
        config = self._prepare(converter_logic, Path("/audio/kick.wav"), is_file=True)

        plan = converter_logic._conversion_plan(config, Path("/audio/kick.wav"))

        assert isinstance(plan, GroupConversion)
        assert plan.sources == (Path("/audio/kick.wav"),)

    def test_a_directory_becomes_a_directory_conversion(self, converter_logic: ConverterLogic) -> None:
        config = self._prepare(converter_logic, Path("/audio"), is_file=False)

        plan = converter_logic._conversion_plan(config, Path("/audio"))

        assert isinstance(plan, DirectoryConversion)
        assert plan.directory == Path("/audio")

    def test_the_setup_covers_every_enabled_channel(self, converter_logic: ConverterLogic) -> None:
        """With no stems listed, one stem holds every channel the configuration enables."""
        config = self._prepare(converter_logic, Path("/audio/kick.wav"), is_file=True)
        channels = list(config.generation.channels)

        plan = converter_logic._conversion_plan(config, Path("/audio/kick.wav"))

        assert plan.stems == StemsConfig.single_entry(channels, channel_cap=len(channels))
        assert plan.stems.covered_channels == frozenset(channels)

    def test_starting_hands_the_plan_to_the_service(self, converter_logic: ConverterLogic) -> None:
        config = self._prepare(converter_logic, Path("/audio/kick.wav"), is_file=True)
        converter_logic._config_manager.config = config

        converter_logic._start_conversion()

        started_config, started_plan = converter_logic._service.start.call_args.args
        assert started_config == config
        assert isinstance(started_plan, GroupConversion)


class TestStemsSetup:
    """The rows a reader gathers, and the setup they turn into."""

    def _with_config(self, converter_logic: ConverterLogic) -> Config:
        config = Config()
        converter_logic._config_manager.config = config
        return config

    def test_selecting_a_recording_in_stems_mode_adds_it(self, converter_logic: ConverterLogic) -> None:
        self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)

        converter_logic.select_source(Path("/audio/bass.wav"))
        converter_logic.select_source(Path("/audio/lead.wav"))

        assert converter_logic._source_paths == (Path("/audio/bass.wav"), Path("/audio/lead.wav"))

    def test_adding_a_listed_recording_leaves_the_list_as_it_is(self, converter_logic: ConverterLogic) -> None:
        self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/bass.wav"), Path("/audio/lead.wav")])
        converter_logic.isolate_source(Path("/audio/lead.wav"))

        converter_logic.add_sources([Path("/audio/lead.wav")])

        assert converter_logic._source_paths == (Path("/audio/bass.wav"), Path("/audio/lead.wav"))
        assert converter_logic._levels.level_of(Path("/audio/lead.wav")) == 1

    def test_the_list_stops_at_the_room_it_has(self, converter_logic: ConverterLogic) -> None:
        self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)

        converter_logic.add_sources([Path(f"/audio/{index}.wav") for index in range(MAX_STEM_SOURCES + 3)])

        assert converter_logic.source_count == MAX_STEM_SOURCES

    def test_removing_a_recording_takes_it_out(self, converter_logic: ConverterLogic) -> None:
        self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav"), Path("/audio/b.wav")])

        converter_logic.remove_source(Path("/audio/a.wav"))

        assert converter_logic._source_paths == (Path("/audio/b.wav"),)

    def test_entering_stems_mode_carries_the_selected_file_in(self, converter_logic: ConverterLogic) -> None:
        self._with_config(converter_logic)
        converter_logic._input_path = Path("/audio/kick.wav")
        converter_logic._is_file = True

        converter_logic.set_stems_mode(True)

        assert converter_logic._source_paths == (Path("/audio/kick.wav"),)

    def test_leaving_stems_mode_keeps_the_first_recording(self, converter_logic: ConverterLogic) -> None:
        self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav"), Path("/audio/b.wav")])

        converter_logic.set_stems_mode(False)

        assert converter_logic._levels.paths == (Path("/audio/a.wav"),)

    def test_a_stems_conversion_groups_every_listed_recording(self, converter_logic: ConverterLogic) -> None:
        config = self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav"), Path("/audio/b.wav")])

        plan = converter_logic._conversion_plan(config, Path("/audio/a.wav"))

        assert isinstance(plan, GroupConversion)
        assert plan.sources == (Path("/audio/a.wav"), Path("/audio/b.wav"))
        assert [entry.id for entry in plan.stems.entries] == [0, 1]

    def test_the_rows_channels_and_levels_reach_the_setup(self, converter_logic: ConverterLogic) -> None:
        config = self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav"), Path("/audio/b.wav")])
        converter_logic.set_source_channels(Path("/audio/a.wav"), frozenset({ChannelName.PULSE1}))
        converter_logic.isolate_source(Path("/audio/b.wav"))

        plan = converter_logic._conversion_plan(config, Path("/audio/a.wav"))

        assert plan.stems.entries[0].channels == [ChannelName.PULSE1]
        assert plan.stems.hierarchy.levels == [[0], [1]]

    def test_a_recording_left_with_no_channel_takes_no_part(self, converter_logic: ConverterLogic) -> None:
        config = self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav"), Path("/audio/b.wav")])

        converter_logic.set_source_channels(Path("/audio/a.wav"), frozenset())
        plan = converter_logic._conversion_plan(config, Path("/audio/a.wav"))

        assert converter_logic.source_count == 2
        assert plan.sources == (Path("/audio/b.wav"),)
        assert [entry.id for entry in plan.stems.entries] == [0]

    def test_a_row_reports_the_level_it_landed_on(self, converter_logic: ConverterLogic) -> None:
        config = self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav"), Path("/audio/b.wav")])

        converter_logic.move_source_to_new_level(Path("/audio/b.wav"), 0)
        rows = converter_logic._stem_rows(config)

        assert [(row.path.name, row.level, row.level_count) for row in rows] == [
            ("b.wav", 0, 2),
            ("a.wav", 1, 2),
        ]

    def test_the_cap_holds_within_the_channels_enabled(self, converter_logic: ConverterLogic) -> None:
        config = self._with_config(converter_logic)
        channels = list(config.generation.channels)

        converter_logic.set_channel_cap(len(channels) + 5)

        assert converter_logic._effective_channel_cap == len(channels)

    def test_a_cap_below_one_is_refused(self, converter_logic: ConverterLogic) -> None:
        self._with_config(converter_logic)

        converter_logic.set_channel_cap(0)

        assert converter_logic._effective_channel_cap == MIN_CHANNEL_CAP

    def test_the_cap_reaches_a_classic_conversion_too(self, converter_logic: ConverterLogic) -> None:
        """One recording per frame is a choice a reader makes for every conversion, batch included."""
        config = self._with_config(converter_logic)
        converter_logic._input_path = Path("/audio/kick.wav")
        converter_logic._is_file = True
        converter_logic.set_channel_cap(1)

        plan = converter_logic._conversion_plan(config, Path("/audio/kick.wav"))

        assert plan.stems.channel_cap == 1

    def test_the_hierarchy_mode_reaches_the_setup(self, converter_logic: ConverterLogic) -> None:
        config = self._with_config(converter_logic)
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav")])

        converter_logic.set_hierarchy_mode(HierarchyMode.STRICT)

        plan = converter_logic._conversion_plan(config, Path("/audio/a.wav"))
        assert plan.stems.hierarchy.mode == HierarchyMode.STRICT


class TestStemsView:
    """What the panel is told about the setup being built."""

    def _emitted(self, converter_logic: ConverterLogic) -> ConverterViewModel:
        return converter_logic.on_view_changed.call_args.args[0]

    def test_the_rows_reach_the_view_in_list_order(self, converter_logic: ConverterLogic) -> None:
        converter_logic._config_manager.config = Config()
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav"), Path("/audio/b.wav")])

        view_model = self._emitted(converter_logic)

        assert [row.name for row in view_model.stem_sources] == ["a", "b"]
        assert view_model.stems_mode is True
        assert view_model.has_input is True

    def test_a_row_shows_the_channels_it_may_take(self, converter_logic: ConverterLogic) -> None:
        converter_logic._config_manager.config = Config()
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path("/audio/a.wav")])
        converter_logic.set_source_channels(Path("/audio/a.wav"), frozenset({ChannelName.NOISE}))

        assert self._emitted(converter_logic).stem_sources[0].channels == frozenset({ChannelName.NOISE})

    def test_the_view_states_whether_another_recording_fits(self, converter_logic: ConverterLogic) -> None:
        converter_logic._config_manager.config = Config()
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources([Path(f"/audio/{index}.wav") for index in range(MAX_STEM_SOURCES)])

        view_model = self._emitted(converter_logic)

        assert view_model.source_count == MAX_STEM_SOURCES
        assert view_model.can_add_source is False

    def test_an_empty_stems_list_offers_nothing_to_convert(self, converter_logic: ConverterLogic) -> None:
        converter_logic._config_manager.config = Config()
        converter_logic.set_stems_mode(True)

        view_model = self._emitted(converter_logic)

        assert view_model.has_input is False
        assert view_model.convert_button_enabled is False


class TestProgressText:
    """A batch counts the files it has written; a single job names the reconstruction it is making."""

    def _progress(self, completed: int, total: int) -> ServiceProgress[Path]:
        return ServiceProgress(completed=completed, total=total, eta_seconds=None, current_item=None)

    def _status(self, converter_logic: ConverterLogic) -> str:
        view_model = converter_logic.on_view_changed.call_args.args[0]
        return str(view_model.status_text)

    def test_a_batch_counts_its_files(self, converter_logic: ConverterLogic) -> None:
        converter_logic._handle_progress_result(self._progress(2, 5))

        assert self._status(converter_logic) == "Progress: 2/5 files"

    def test_a_single_job_names_the_reconstruction_it_writes(self, converter_logic: ConverterLogic) -> None:
        converter_logic._output_path = Path("/reconstructions/track.stn")

        converter_logic._handle_progress_result(self._progress(0, 1))

        assert self._status(converter_logic) == "Reconstructing track..."

    def test_a_single_job_falls_back_to_the_selected_input(self, converter_logic: ConverterLogic) -> None:
        converter_logic._output_path = None
        converter_logic._input_path = Path("/audio/kick.wav")

        converter_logic._handle_progress_result(self._progress(0, 1))

        assert self._status(converter_logic) == "Reconstructing kick..."
