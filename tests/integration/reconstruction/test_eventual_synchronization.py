import random
from typing import Callable, Dict, Final, List, Tuple

import pytest

from sampletones_application.application import Application
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.reconstruction.rewrites.steps import StemRemovalRequest
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_application.view_model.reconstruction.instruments import (
    InstrumentsShowing,
    ReconstructionInstrumentsViewModel,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from tests.suite.application import HeldQueue, held_queue
from tests.suite.headless import app
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, STEM_A_ID, STEM_B_ID, taking_turns

__all__ = ["app", "held_queue", "taking_turns"]

STEPS: Final[int] = 40
SEEDS: Final[range] = range(12)
LOUDEST: Final[int] = 15
LONGEST_DRAG: Final[int] = 4
STEMS: Final[Tuple[int, ...]] = (STEM_A_ID, STEM_B_ID)
CHANNELS: Final[Tuple[ChannelName, ...]] = (SHARED_CHANNEL, SOLE_CHANNEL)

Gesture = Callable[[], None]


@pytest.fixture
def turns_sample(
    app: Application,
    held_queue: HeldQueue,
    taking_turns: Reconstruction,
) -> Sample:
    """The two-recording document added to a new project and opened on the tab, its opening landed."""
    app.project_controller.new()
    with app.history.transaction(HistoryAction.ADD_SAMPLE):
        sample = app.project_controller.add_sample(taking_turns, "turns")
    app._reconstruction_coordinator.open_project_voice(sample.id)
    _settle(app, held_queue)
    return sample


def _land(app: Application, held_queue: HeldQueue) -> None:
    """Lets the worker finish what it runs and lands its report, which may start the next step."""
    SingleThreadExecutor.join_all()
    held_queue.drain()


def _settle(app: Application, held_queue: HeldQueue) -> None:
    """Lands every step until the line stands idle."""
    _land(app, held_queue)
    while app.reconstruction_rewrites.is_busy:
        _land(app, held_queue)


def _gestures(
    app: Application,
    held_queue: HeldQueue,
    chance: random.Random,
) -> Dict[str, Gesture]:
    """Every gesture the reader can make on the open document, each drawing its own choices."""
    panel = app._reconstructions_tab._reconstruction_panel_logic
    instruments = app._reconstructions_tab._reconstruction_instruments_logic
    coordinator = app._reconstruction_coordinator
    floor = app.history.cursor

    def tick() -> None:
        stem = chance.choice(STEMS)
        heard = frozenset(channel for channel in CHANNELS if chance.random() < 0.5)
        panel.set_stem_channels(stem, heard)

    def boxes() -> None:
        panel.set_selected_channels([channel for channel in CHANNELS if chance.random() < 0.5])

    def solo() -> None:
        panel.solo_stem(chance.choice(STEMS))

    def drag() -> None:
        items = tuple(chance.randint(0, LOUDEST) for _ in range(chance.randint(1, LONGEST_DRAG)))
        instruments.handle_envelope_changed(chance.choice(CHANNELS), FeatureKey.VOLUME, Envelope[int](items=items))

    def silence() -> None:
        instruments.handle_envelope_changed(chance.choice(CHANNELS), FeatureKey.VOLUME, Envelope[int](items=(0,)))

    def remove() -> None:
        coordinator.request_rewrite(StemRemovalRequest(stem_id=chance.choice(STEMS), stem_name="gone"))

    def undo_an_edit() -> None:
        """Undoes the latest edit, keeping the sample's own addition, so the document stays open."""
        if app.history.cursor > floor:
            app.history.undo()

    def undo() -> None:
        coordinator.after_edits(undo_an_edit)

    def land() -> None:
        _land(app, held_queue)

    return {
        "tick": tick,
        "boxes": boxes,
        "solo": solo,
        "drag": drag,
        "silence": silence,
        "remove": remove,
        "undo": undo,
        "land": land,
    }


def _expect_caught_up(
    app: Application,
    views: List[ReconstructionInstrumentsViewModel],
    walk: List[str],
) -> None:
    """The open document's envelopes answer what the reader hears, the waveform owes nothing, and the instruments
    panel draws the envelopes, free to edit.
    """
    manager = app.reconstruction_manager
    panel = app._reconstructions_tab._reconstruction_panel_logic
    assert not app.reconstruction_rewrites.is_busy, walk
    assert manager.reconstruction is not None, walk
    assert manager.current_features is not None, walk
    assert panel._owed is None, walk
    assert views, walk
    assert views[-1].showing is InstrumentsShowing.EDITABLE, walk


class TestTheInstrumentsPanelCatchesUpWithEveryWalk:
    """The instruments panel keeps the envelopes it drew through every gesture on an open document, and catches
    up once the reader stops.

    A seeded walk of ticks, channel boxes, solos, drags, silencings, removals and undos, each
    landed or left on its way at random, ends with the line drained. Every view the panel was
    handed must draw or keep envelopes, and at the end the envelopes must answer the open
    document and the reader's choice, the waveform must owe nothing, and the panel must be free
    to edit. A recording ticked away and back before the first listening lands is the gesture that
    left the panel waiting for good: that listening landed envelopes for the choice the reader had
    left.
    """

    def test_a_recording_ticked_away_and_back_before_the_listening_lands(
        self,
        app: Application,
        held_queue: HeldQueue,
        turns_sample: Sample,
    ) -> None:
        panel = app._reconstructions_tab._reconstruction_panel_logic
        views: List[ReconstructionInstrumentsViewModel] = []
        app._reconstructions_tab._reconstruction_instruments_logic.on_view_changed = views.append
        heard = app.reconstruction_manager.listening.heard[STEM_B_ID]

        panel.set_stem_channels(STEM_B_ID, frozenset())
        panel.set_stem_channels(STEM_B_ID, heard)
        _settle(app, held_queue)

        _expect_caught_up(app, views, ["tick away", "tick back"])

    @pytest.mark.parametrize("seed", SEEDS)
    def test_every_view_draws_or_keeps_the_envelopes(
        self,
        seed: int,
        app: Application,
        held_queue: HeldQueue,
        turns_sample: Sample,
    ) -> None:
        chance = random.Random(seed)
        gestures = _gestures(app, held_queue, chance)
        views: List[ReconstructionInstrumentsViewModel] = []
        app._reconstructions_tab._reconstruction_instruments_logic.on_view_changed = views.append
        walk: List[str] = []

        for _ in range(STEPS):
            name = chance.choice(list(gestures))
            walk.append(name)
            gestures[name]()

        _settle(app, held_queue)

        assert all(view.is_open for view in views), walk
        _expect_caught_up(app, views, walk)
