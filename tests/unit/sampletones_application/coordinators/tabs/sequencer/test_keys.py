from pathlib import Path
from typing import Final, List, Mapping, Optional, Tuple

import pytest

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.tabs.sequencer.keys import TrackerKeys
from sampletones_application.logic.shared.live import Keyboard, LiveKey
from sampletones_application.ui.panels.sequencer.input.edit import EnteredNote
from sampletones_core.constants.enums import ChannelName
from sampletones_core.performance import velocity_levels
from sampletones_shared.types.callback import VoidCallback
from tests.suite.headless import profile_in

NOTE: Final[int] = 64
SOFT: Final[int] = 30
ROW: Final[int] = 5
KEY_CODE: Final[int] = 90


class Tracker:
    """The tracker as its keys reach it: whether it takes notes, and the notes entered, each at the next row."""

    def __init__(self) -> None:
        self.taking: bool = True
        self.entered: List[Tuple[int, Optional[Mapping[ChannelName, int]]]] = []

    def takes_notes(self) -> bool:
        return self.taking

    def enter_note(self, pitch: int, *, levels: Optional[Mapping[ChannelName, int]]) -> Optional[EnteredNote]:
        self.entered.append((pitch, levels))
        return EnteredNote(row=ROW + len(self.entered) - 1, channel=ChannelName.PULSE2)


class Sounds:
    """What the keys asked the row's sound for, in the order asked."""

    def __init__(self) -> None:
        self.asked: List[Tuple[str, LiveKey, Optional[int], Optional[ChannelName]]] = []

    def strike(self, key: LiveKey, row_index: int, channel: Optional[ChannelName]) -> None:
        self.asked.append(("strike", key, row_index, channel))

    def lift(self, key: LiveKey) -> None:
        self.asked.append(("lift", key, None, None))


class RenderThread:
    """The render thread's queue: what is posted waits there until the case runs it."""

    def __init__(self) -> None:
        self.posted: List[VoidCallback] = []

    def post(self, delivery: VoidCallback) -> None:
        self.posted.append(delivery)

    def run(self) -> None:
        posted, self.posted = self.posted, []
        for delivery in posted:
            delivery()


@pytest.fixture
def tracker() -> Tracker:
    return Tracker()


@pytest.fixture
def sounds() -> Sounds:
    return Sounds()


@pytest.fixture
def render_thread() -> RenderThread:
    return RenderThread()


@pytest.fixture
def session(tmp_path: Path) -> SessionManager:
    return SessionManager(profile_in(tmp_path))


@pytest.fixture
def keys(tracker: Tracker, sounds: Sounds, session: SessionManager, render_thread: RenderThread) -> TrackerKeys:
    return TrackerKeys(tracker, sounds, session, post=render_thread.post)


def _midi(note: int) -> LiveKey:
    return LiveKey(keyboard=Keyboard.MIDI, number=note)


class TestAMidiKeyInTheTracker:
    """A MIDI key enters its note on the render thread and sounds the row it wrote, its lift following it there."""

    def test_a_key_enters_nothing_until_the_render_thread_runs_it(
        self,
        keys: TrackerKeys,
        tracker: Tracker,
        sounds: Sounds,
        render_thread: RenderThread,
    ) -> None:
        keys.press(NOTE, SOFT)

        assert tracker.entered == []
        render_thread.run()
        assert [pitch for pitch, _ in tracker.entered] == [NOTE]
        assert sounds.asked == [("strike", _midi(NOTE), ROW, ChannelName.PULSE2)]

    def test_a_lift_follows_its_press_on_the_render_thread(
        self,
        keys: TrackerKeys,
        sounds: Sounds,
        render_thread: RenderThread,
    ) -> None:
        keys.press(NOTE, SOFT)
        keys.lift(NOTE)

        render_thread.run()

        assert [asked[0] for asked in sounds.asked] == ["strike", "lift"]
        assert sounds.asked[1][1] == _midi(NOTE)

    def test_a_key_writes_the_levels_its_velocity_names(
        self,
        keys: TrackerKeys,
        tracker: Tracker,
        session: SessionManager,
        render_thread: RenderThread,
    ) -> None:
        session.set_midi_settings(None, velocity_sets_volume=True)

        keys.press(NOTE, SOFT)
        render_thread.run()

        assert tracker.entered == [(NOTE, velocity_levels(SOFT))]

    def test_with_velocity_off_a_key_leaves_the_volume_alone(
        self,
        keys: TrackerKeys,
        tracker: Tracker,
        session: SessionManager,
        render_thread: RenderThread,
    ) -> None:
        session.set_midi_settings(None, velocity_sets_volume=False)

        keys.press(NOTE, SOFT)
        render_thread.run()

        assert tracker.entered == [(NOTE, None)]

    def test_a_tracker_that_stopped_taking_notes_enters_nothing(
        self,
        keys: TrackerKeys,
        tracker: Tracker,
        sounds: Sounds,
        render_thread: RenderThread,
    ) -> None:
        """The scope was published a frame before the key reached the render thread, so the press asks again."""
        keys.press(NOTE, SOFT)
        tracker.taking = False

        render_thread.run()

        assert tracker.entered == []
        assert sounds.asked == []
        tracker.taking = True
        keys.press(NOTE, SOFT)
        render_thread.run()
        assert len(tracker.entered) == 1


class TestAComputerKeyInTheTracker:
    def test_a_piano_key_sounds_the_cell_it_entered(self, keys: TrackerKeys, sounds: Sounds) -> None:
        keys.computer_key_entered(KEY_CODE, ROW, None)

        assert sounds.asked == [("strike", LiveKey(keyboard=Keyboard.COMPUTER, number=KEY_CODE), ROW, None)]

    def test_a_piano_key_released_lifts_its_own_key(self, keys: TrackerKeys, sounds: Sounds) -> None:
        keys.computer_key_released(KEY_CODE)

        assert sounds.asked == [("lift", LiveKey(keyboard=Keyboard.COMPUTER, number=KEY_CODE), None, None)]
