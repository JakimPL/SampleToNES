from dataclasses import dataclass
from pathlib import Path
from typing import Final, FrozenSet, Tuple

import pytest

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


def view(*rows: StemRowViewModel, collapse_levels: bool) -> StemsListViewModel:
    return StemsListViewModel(
        rows=rows,
        channels_in_play=CHANNELS,
        muted_channels=frozenset(),
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
) -> StemsMessages:
    """The answers one list would give, reading the view it is drawing."""
    answering = StemsMessages(
        LANGUAGE_MANAGER,
        offer=offer(dragging=dragging),
        open_folders=open_folders,
        host=host,
    )
    answering.reads(view(*rows, collapse_levels=collapse_levels))
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
