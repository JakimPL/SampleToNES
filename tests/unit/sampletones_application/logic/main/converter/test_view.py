from pathlib import Path
from typing import Final, Optional

from sampletones_application.constants.output import OutputKind
from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.settings import RunSettings
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.converter.view import source_settings
from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_application.view_model.main.source import (
    ChannelSettingsViewModel,
    SourceSettingsPanelViewModel,
)
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE, UNIT_DRIVE
from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.unit.sampletones_application.logic.main.sources.factories import folder, recording

LOUD_DRIVE: Final[float] = 2.0
JOINING: Final[StemSettings] = StemSettings.covering(list(DEFAULT_CHANNELS))
FOLDER_ROOT: Final[str] = "/audio/loops"
PICKED: Final[str] = "/audio/kick.wav"


def _state(
    *recordings: Recording,
    selected: Optional[SourceKey] = None,
    joining: StemSettings = JOINING,
) -> ConverterState:
    """A converter holding these recordings, with ``selected`` inspected."""
    gathering = Gathering.empty()
    for item in recordings:
        gathering = gathering.listing(item)

    return ConverterState(
        settings=RunSettings(
            joining=joining,
            output=OutputKind.PER_RECORDING,
            hierarchy_mode=DEFAULT_STEMS_HIERARCHY_MODE,
        ),
        gathering=gathering,
        destination=Destination.unset(),
        selected=selected,
    )


def _folder_state(*recordings: Recording) -> ConverterState:
    """A converter holding one folder standing for these recordings, the folder inspected."""
    state = _state(selected=SourceKey.folder(Path(FOLDER_ROOT)))
    return state.with_gathering(state.gathering.listing_folder(folder(FOLDER_ROOT, recordings)))


def _card(state: ConverterState, *, live: bool = True) -> SourceSettingsPanelViewModel:
    return source_settings(state, live=live)


def _channel(
    view_model: SourceSettingsPanelViewModel,
    channel_name: ChannelName,
) -> ChannelSettingsViewModel:
    return next(channel for channel in view_model.channels if channel.channel is channel_name)


class TestWhatTheCardIsPointedAt(BaseTestSuite):
    def test_with_nothing_picked_it_edits_what_a_recording_joins_with(self) -> None:
        view_model = _card(_state(recording("/audio/kick.wav")))

        assert view_model.subject is None
        assert view_model.edits_new_recordings is True

    def test_it_reads_the_settings_a_recording_joins_with(self) -> None:
        joining = StemSettings.covering([ChannelName.NOISE]).with_channel_cap(1)

        view_model = _card(_state(recording("/audio/kick.wav"), joining=joining))

        assert _channel(view_model, ChannelName.NOISE).use is Agreement.ALL
        assert _channel(view_model, ChannelName.PULSE1).use is Agreement.NONE
        assert view_model.channel_cap == 1

    def test_a_picked_recording_names_the_card(self) -> None:
        state = _state(
            recording("/audio/kick.wav"),
            selected=SourceKey.recording(Path("/audio/kick.wav")),
        )

        subject = _card(state).subject

        assert subject is not None
        assert (subject.name, subject.holds) == ("kick", 1)

    def test_a_row_the_list_lets_go_of_falls_back_to_the_joining_settings(self) -> None:
        state = _state(selected=SourceKey.recording(Path("/audio/gone.wav")))

        view_model = _card(state)

        assert view_model.edits_new_recordings is True
        assert _channel(view_model, ChannelName.PULSE1).use is Agreement.ALL

    def test_a_conversion_under_way_holds_the_card_still(self) -> None:
        assert _card(_state(), live=False).live is False


class TestHowOneRecordingReads(BaseTestSuite):
    @staticmethod
    def _picked(item: Recording) -> SourceSettingsPanelViewModel:
        return _card(_state(item, selected=SourceKey.recording(item.path)))

    def test_a_channel_it_occupies_reads_as_held(self) -> None:
        view_model = self._picked(recording(PICKED, [ChannelName.PULSE1]))

        assert _channel(view_model, ChannelName.PULSE1).use is Agreement.ALL
        assert _channel(view_model, ChannelName.TRIANGLE).use is Agreement.NONE

    def test_a_channel_it_bends_reads_as_bent(self) -> None:
        view_model = self._picked(recording(PICKED, [ChannelName.TRIANGLE], [ChannelName.TRIANGLE]))

        assert _channel(view_model, ChannelName.TRIANGLE).bend is Agreement.ALL

    def test_the_noise_channel_reads_no_bend(self) -> None:
        view_model = self._picked(recording(PICKED, [ChannelName.NOISE]))

        noise = _channel(view_model, ChannelName.NOISE)
        assert (noise.bend, noise.bendable) == (Agreement.NONE, False)

    def test_the_drive_it_gives_a_channel_reads_back(self) -> None:
        view_model = self._picked(recording(PICKED, [ChannelName.PULSE1], drives={ChannelName.PULSE1: LOUD_DRIVE}))

        assert _channel(view_model, ChannelName.PULSE1).drive == LOUD_DRIVE

    def test_a_channel_it_leaves_free_rests_at_the_calibrated_level(self) -> None:
        view_model = self._picked(recording(PICKED, [ChannelName.PULSE1]))

        triangle = _channel(view_model, ChannelName.TRIANGLE)
        assert (triangle.drive, triangle.drive_mixed) == (UNIT_DRIVE, False)

    def test_the_count_it_holds_reads_back(self) -> None:
        view_model = self._picked(recording(PICKED, [ChannelName.PULSE1, ChannelName.TRIANGLE], channel_cap=1))

        assert view_model.channel_cap == 1
        assert view_model.step_agreement(1) is Agreement.ALL
        assert view_model.step_agreement(2) is Agreement.NONE

    def test_a_step_past_the_channels_it_occupies_reaches_nothing(self) -> None:
        view_model = self._picked(recording(PICKED, [ChannelName.PULSE1, ChannelName.TRIANGLE]))

        assert (view_model.channels_used, view_model.step_reaches(2), view_model.step_reaches(3)) == (2, True, False)


class TestHowAFolderReads(BaseTestSuite):
    """Recordings that differ read half-lit, the way they do in the list."""

    def test_a_channel_only_some_of_them_occupy_reads_as_half_held(self) -> None:
        view_model = _card(
            _folder_state(
                recording(f"{FOLDER_ROOT}/a.wav", [ChannelName.PULSE1]),
                recording(f"{FOLDER_ROOT}/b.wav", [ChannelName.TRIANGLE]),
            )
        )

        assert _channel(view_model, ChannelName.PULSE1).use is Agreement.SOME

    def test_drives_they_differ_on_read_as_mixed(self) -> None:
        view_model = _card(
            _folder_state(
                recording(f"{FOLDER_ROOT}/a.wav", [ChannelName.PULSE1], drives={ChannelName.PULSE1: LOUD_DRIVE}),
                recording(f"{FOLDER_ROOT}/b.wav", [ChannelName.PULSE1]),
            )
        )

        pulse = _channel(view_model, ChannelName.PULSE1)
        assert (pulse.drive, pulse.drive_mixed, pulse.drive_shown) == (None, True, UNIT_DRIVE)

    def test_one_drive_they_agree_on_reads_plainly(self) -> None:
        view_model = _card(
            _folder_state(
                recording(f"{FOLDER_ROOT}/a.wav", [ChannelName.PULSE1], drives={ChannelName.PULSE1: LOUD_DRIVE}),
                recording(f"{FOLDER_ROOT}/b.wav", [ChannelName.PULSE1], drives={ChannelName.PULSE1: LOUD_DRIVE}),
            )
        )

        assert _channel(view_model, ChannelName.PULSE1).drive == LOUD_DRIVE

    def test_counts_they_differ_on_leave_every_step_half_lit(self) -> None:
        view_model = _card(
            _folder_state(
                recording(f"{FOLDER_ROOT}/a.wav", [ChannelName.PULSE1, ChannelName.TRIANGLE], channel_cap=1),
                recording(f"{FOLDER_ROOT}/b.wav", [ChannelName.PULSE1, ChannelName.TRIANGLE], channel_cap=2),
            )
        )

        assert view_model.channel_cap is None
        assert view_model.step_agreement(1) is Agreement.SOME
        assert view_model.step_agreement(2) is Agreement.SOME
        assert view_model.step_agreement(3) is Agreement.NONE

    def test_the_channels_used_is_the_most_any_of_them_occupies(self) -> None:
        view_model = _card(
            _folder_state(
                recording(f"{FOLDER_ROOT}/a.wav", [ChannelName.PULSE1]),
                recording(f"{FOLDER_ROOT}/b.wav", [ChannelName.PULSE1, ChannelName.TRIANGLE]),
            )
        )

        assert view_model.channels_used == 2

    def test_the_folder_names_how_many_recordings_it_stands_for(self) -> None:
        view_model = _card(
            _folder_state(
                recording(f"{FOLDER_ROOT}/a.wav"),
                recording(f"{FOLDER_ROOT}/b.wav"),
            )
        )

        subject = view_model.subject
        assert subject is not None
        assert (subject.holds, subject.stands_for_a_folder) == (2, True)
