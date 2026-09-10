from dataclasses import dataclass
from pathlib import Path
from typing import Final, FrozenSet, Tuple

import pytest

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SourceKind
from sampletones_application.paths import LANG_EN
from sampletones_application.ui.elements.stems.expansion import OpenFolders
from sampletones_application.ui.elements.stems.messages import StemsMessages
from sampletones_application.ui.elements.stems.offer import StemsListOffer
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.TRIANGLE)
NAME: Final[str] = "kick"
FOLDER_NAME: Final[str] = "sources"
HOLDS: Final[int] = 3


@dataclass(frozen=True)
class Host:
    """What the list answers about the gestures its owner takes, as ``StemsListHost`` states them."""

    activatable: bool = False
    playable: bool = False
    has_menu: bool = False


def offer(*, dragging: bool = False) -> StemsListOffer:
    return StemsListOffer(
        master_box=False,
        removal=True,
        keeps_last_row=False,
        dragging=dragging,
        bends=False,
        picking=False,
    )


def recording(
    name: str = NAME,
    *,
    channels: FrozenSet[ChannelName] = frozenset(CHANNELS),
    offered_channels: FrozenSet[ChannelName] = frozenset(CHANNELS),
    available: bool = True,
) -> StemRowViewModel:
    path = Path(f"/audio/{name}.wav")
    return StemRowViewModel(
        key=str(path),
        kind=SourceKind.RECORDING,
        path=path,
        held=(),
        channels=channels,
        partial_channels=frozenset(),
        bends=frozenset(),
        offered_channels=offered_channels,
        available=available,
        level=0,
        position=0,
        level_size=1,
        level_count=1,
    )


def folder(name: str = FOLDER_NAME, *, holds: int = HOLDS) -> StemRowViewModel:
    root = Path(f"/audio/{name}")
    return StemRowViewModel(
        key=str(root),
        kind=SourceKind.FOLDER,
        path=root,
        held=tuple(recording(f"{name}/take_{index}") for index in range(holds)),
        channels=frozenset(CHANNELS),
        partial_channels=frozenset(),
        bends=frozenset(),
        offered_channels=frozenset(CHANNELS),
        available=True,
        level=0,
        position=0,
        level_size=1,
        level_count=1,
    )


def view(
    *rows: StemRowViewModel,
    collapse_levels: bool,
    muted_channels: FrozenSet[ChannelName] = frozenset(),
) -> StemsListViewModel:
    return StemsListViewModel(
        rows=rows,
        channels_in_play=CHANNELS,
        muted_channels=muted_channels,
        picked_keys=frozenset(),
        picking_room=None,
        live=True,
        collapse_levels=collapse_levels,
        selected_key=None,
    )


def messages(
    *rows: StemRowViewModel,
    collapse_levels: bool,
    dragging: bool = False,
    host: Host = Host(),
    open_folders: OpenFolders = OpenFolders(),
    muted_channels: FrozenSet[ChannelName] = frozenset(),
) -> StemsMessages:
    """The answers one list would give, reading the view it is drawing."""
    answering = StemsMessages(
        LANGUAGE_MANAGER,
        offer=offer(dragging=dragging),
        open_folders=open_folders,
        host=host,
    )
    answering.reads(view(*rows, collapse_levels=collapse_levels, muted_channels=muted_channels))
    return answering


def template(key: str) -> str:
    return LANGUAGE_MANAGER[f"global.stems.message.{key}"]


class TestWhatARowSaysAboutDragging(BaseTestSuite):
    """A list drags its rows where it bands them, since a drag moves a recording between levels.

    What the row offers and what it says it offers are one answer, so a list drawing its rows in
    one run neither takes a drag nor speaks of one.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        dragging: bool
        collapse_levels: bool

    test_cases = (
        TestCase(label="a_banded_list_that_drags_says_so", dragging=True, collapse_levels=False, expected=True),
        TestCase(label="one_run_of_rows_takes_no_drag", dragging=True, collapse_levels=True, expected=False),
        TestCase(label="a_list_that_never_drags_stays_quiet", dragging=False, collapse_levels=False, expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_hover_names_the_drag_where_the_row_takes_one(self, test_case: TestCase) -> None:
        kick = recording()

        explanation = messages(
            kick,
            collapse_levels=test_case.collapse_levels,
            dragging=test_case.dragging,
        ).row_explanation(kick)

        assert (template("drag_tooltip") in explanation) is test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_status_line_names_the_drag_where_the_row_takes_one(self, test_case: TestCase) -> None:
        kick = recording()

        line = messages(
            kick,
            collapse_levels=test_case.collapse_levels,
            dragging=test_case.dragging,
        ).name(user_data=kick.key)

        drag = template("status_row_drag").format(name=kick.name)
        assert (drag in line) is test_case.expected


class TestWhatARowSaysAboutTheClickItTakes(BaseTestSuite):
    """A click reaches the owner wherever one answers, so the line naming it stands beside the
    drag rather than behind it."""

    def test_a_list_drawing_one_run_of_rows_names_the_click(self) -> None:
        kick = recording()

        line = messages(kick, collapse_levels=True, dragging=True, host=Host(activatable=True)).name(user_data=kick.key)

        assert template("status_row_reveal").format(name=kick.name) in line

    def test_a_banded_list_names_the_drag_and_the_click_together(self) -> None:
        kick = recording()

        line = messages(kick, collapse_levels=False, dragging=True, host=Host(activatable=True)).name(
            user_data=kick.key
        )

        assert template("status_row_drag").format(name=kick.name) in line
        assert template("status_row_reveal").format(name=kick.name) in line

    def test_a_list_no_owner_answers_reads_as_the_name_alone(self) -> None:
        """A double-click is the one gesture nothing on the row draws, so a list that neither
        sounds nor reveals has nothing to offer beyond what the row is called."""
        kick = recording()

        line = messages(kick, collapse_levels=True).name(user_data=kick.key)

        assert line == kick.name

    def test_a_list_that_sounds_a_row_says_so(self) -> None:
        kick = recording()

        line = messages(kick, collapse_levels=True, host=Host(playable=True)).name(user_data=kick.key)

        assert template("status_row_play").format(name=kick.name) in line


class TestWhatARowExplainsOnHover(BaseTestSuite):
    """The hover names where the recording is, and why it is grayed out where it contributes
    nothing, so a reader meets the reason beside the row it belongs to."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        row: StemRowViewModel
        key: str

    test_cases = (
        TestCase(label="a_folder_stands_for_what_it_holds", row=folder(), key="folder_tooltip"),
        TestCase(
            label="a_recording_off_disk_says_so",
            row=recording(available=False),
            key="missing_tooltip",
        ),
        TestCase(
            label="a_recording_holding_no_frames_says_so",
            row=recording(offered_channels=frozenset()),
            key="unoffered_tooltip",
        ),
        TestCase(
            label="a_recording_on_no_channel_says_what_would_bring_it_in",
            row=recording(channels=frozenset()),
            key="inert_tooltip",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_hover_names_the_reading_the_row_stands_at(self, test_case: TestCase) -> None:
        explanation = messages(test_case.row, collapse_levels=True).row_explanation(test_case.row)

        assert template(test_case.key) in explanation

    def test_the_hover_opens_on_where_the_recording_is(self) -> None:
        kick = recording()

        explanation = messages(kick, collapse_levels=True).row_explanation(kick)

        assert explanation.startswith(str(kick.path))

    def test_a_recording_in_play_explains_itself_by_its_path_alone(self) -> None:
        kick = recording()

        explanation = messages(kick, collapse_levels=True).row_explanation(kick)

        assert explanation == str(kick.path)


class TestWhatAFolderSays(BaseTestSuite):
    """A folder stands for the recordings gathered below it, so its lines name the group rather
    than any one recording in it."""

    def test_its_row_reads_out_how_many_it_holds(self) -> None:
        sources = folder()

        line = messages(sources, collapse_levels=True).name(user_data=sources.key)

        assert line == template("status_folder_row").format(name=sources.name, count=HOLDS)

    def test_its_box_reaches_every_recording_in_it(self) -> None:
        sources = folder()

        line = messages(sources, collapse_levels=True).channel(user_data=(sources.key, ChannelName.PULSE1))

        assert line == template("status_folder_channel").format(
            channel=channel_label(LANGUAGE_MANAGER, ChannelName.PULSE1),
            name=sources.name,
        )

    def test_its_button_takes_the_recordings_with_it(self) -> None:
        sources = folder()

        line = messages(sources, collapse_levels=True).remove(user_data=sources.key)

        assert line == template("status_folder_remove").format(name=sources.name)


class TestWhatTheMarkerSays(BaseTestSuite):
    """The marker beside a folder's name offers the move it would make from where it now stands,
    so the line follows the folder rather than stating one of the two readings."""

    def test_a_closed_folder_offers_to_show_what_it_holds(self) -> None:
        sources = folder()

        line = messages(sources, collapse_levels=True).twisty(user_data=sources.key)

        assert line == template("status_folder_open").format(name=sources.name)

    def test_an_open_folder_offers_to_hide_it_again(self) -> None:
        sources = folder()
        open_folders = OpenFolders()
        open_folders.toggle(sources.key)

        line = messages(sources, collapse_levels=True, open_folders=open_folders).twisty(user_data=sources.key)

        assert line == template("status_folder_close").format(name=sources.name)


class TestWhatABoxSays(BaseTestSuite):
    """A box names the channel it answers for, and a channel switched off everywhere says that
    the row stays quiet on it however the box reads."""

    def test_a_channel_in_play_names_what_the_box_does(self) -> None:
        kick = recording()

        line = messages(kick, collapse_levels=True).channel(user_data=(kick.key, ChannelName.PULSE1))

        assert line == template("status_channel").format(
            channel=channel_label(LANGUAGE_MANAGER, ChannelName.PULSE1),
            name=kick.name,
        )

    def test_a_muted_channel_says_the_row_stays_quiet_on_it(self) -> None:
        kick = recording()

        line = messages(
            kick,
            collapse_levels=True,
            muted_channels=frozenset({ChannelName.PULSE1}),
        ).channel(user_data=(kick.key, ChannelName.PULSE1))

        assert line == template("status_channel_muted").format(
            channel=channel_label(LANGUAGE_MANAGER, ChannelName.PULSE1),
            name=kick.name,
        )

    def test_the_box_beside_a_row_reaches_every_channel(self) -> None:
        kick = recording()

        line = messages(kick, collapse_levels=True).master(user_data=kick.key)

        assert line == template("status_master").format(name=kick.name)

    def test_the_button_takes_the_recording_off_the_list(self) -> None:
        kick = recording()

        line = messages(kick, collapse_levels=True).remove(user_data=kick.key)

        assert line == template("status_remove").format(name=kick.name)


class TestARowTheReadingHasLetGo(BaseTestSuite):
    """A hover is answered a frame after it landed, by which time the list may have moved on, so
    every answer is read from the reading standing now."""

    @pytest.mark.parametrize(
        "answer",
        ("name", "master", "remove", "twisty"),
    )
    def test_a_widget_naming_a_row_that_went_explains_nothing(self, answer: str) -> None:
        answering = messages(recording(), collapse_levels=True)

        assert getattr(answering, answer)(user_data="/audio/gone.wav") == ""

    def test_a_box_naming_a_row_that_went_explains_nothing(self) -> None:
        answering = messages(recording(), collapse_levels=True)

        assert answering.channel(user_data=("/audio/gone.wav", ChannelName.PULSE1)) == ""
