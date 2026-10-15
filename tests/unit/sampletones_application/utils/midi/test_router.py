from typing import Final, List, Tuple

import pytest

from sampletones_application.utils.midi import MidiAllNotesOff, MidiNoteOff, MidiNoteOn, MidiPedal
from sampletones_application.utils.midi.router import MidiRouter

MODAL: Final[int] = 100
PANEL: Final[int] = 60
LOW: Final[int] = 60
HIGH: Final[int] = 67
VELOCITY: Final[int] = 90


class RecordingTarget:
    """A scope's target keeping every press and lift it takes."""

    def __init__(self) -> None:
        self.calls: List[Tuple[str, int]] = []

    def press(self, note: int, velocity: int) -> None:
        del velocity
        self.calls.append(("press", note))

    def lift(self, note: int) -> None:
        self.calls.append(("lift", note))


class Switch:
    """An active predicate a case flips, counting how often it is asked."""

    def __init__(self, on: bool) -> None:
        self.on = on
        self.asked = 0

    def __call__(self) -> bool:
        self.asked += 1
        return self.on


@pytest.fixture
def router() -> MidiRouter:
    return MidiRouter()


def _scope(router: MidiRouter, *, priority: int, on: bool) -> Tuple[RecordingTarget, Switch]:
    target, switch = RecordingTarget(), Switch(on)
    router.register(target, priority=priority, active=switch)
    return target, switch


class TestOfferingAKey:
    """A press goes to the highest scope active at the latest publication, and to none while none is."""

    def test_the_highest_active_scope_takes_a_press(self, router: MidiRouter) -> None:
        panel, _ = _scope(router, priority=PANEL, on=True)
        modal, _ = _scope(router, priority=MODAL, on=True)
        router.publish()

        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))

        assert modal.calls == [("press", LOW)]
        assert panel.calls == []

    def test_an_inactive_scope_leaves_the_press_to_the_next(self, router: MidiRouter) -> None:
        panel, _ = _scope(router, priority=PANEL, on=True)
        modal, _ = _scope(router, priority=MODAL, on=False)
        router.publish()

        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))

        assert panel.calls == [("press", LOW)]
        assert modal.calls == []

    def test_a_press_with_no_active_scope_reaches_nobody_nor_does_its_lift(self, router: MidiRouter) -> None:
        panel, switch = _scope(router, priority=PANEL, on=False)
        router.publish()

        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))
        switch.on = True
        router.publish()
        router.route(MidiNoteOff(note=LOW))

        assert panel.calls == []

    def test_a_change_counts_from_the_next_publication(self, router: MidiRouter) -> None:
        panel, switch = _scope(router, priority=PANEL, on=False)
        router.publish()
        switch.on = True

        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))
        router.publish()
        router.route(MidiNoteOn(note=HIGH, velocity=VELOCITY))

        assert panel.calls == [("press", HIGH)]

    def test_routing_asks_no_scope_whether_it_is_active(self, router: MidiRouter) -> None:
        _, switch = _scope(router, priority=PANEL, on=True)
        router.publish()
        asked = switch.asked

        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))
        router.route(MidiNoteOff(note=LOW))

        assert switch.asked == asked


class TestLiftingAKey:
    """A lift reaches the scope that took the press, whatever is active by then."""

    def test_a_lift_reaches_the_taker_after_a_switch(self, router: MidiRouter) -> None:
        panel, panel_switch = _scope(router, priority=PANEL, on=True)
        modal, modal_switch = _scope(router, priority=MODAL, on=False)
        router.publish()
        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))

        modal_switch.on, panel_switch.on = True, False
        router.publish()
        router.route(MidiNoteOff(note=LOW))

        assert panel.calls == [("press", LOW), ("lift", LOW)]
        assert modal.calls == []

    def test_a_lift_of_a_key_never_pressed_reaches_nobody(self, router: MidiRouter) -> None:
        panel, _ = _scope(router, priority=PANEL, on=True)
        router.publish()

        router.route(MidiNoteOff(note=LOW))

        assert panel.calls == []

    def test_a_key_pressed_again_elsewhere_is_lifted_where_it_was_held(self, router: MidiRouter) -> None:
        panel, panel_switch = _scope(router, priority=PANEL, on=True)
        modal, modal_switch = _scope(router, priority=MODAL, on=False)
        router.publish()
        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))

        modal_switch.on, panel_switch.on = True, False
        router.publish()
        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))
        router.route(MidiNoteOff(note=LOW))

        assert panel.calls == [("press", LOW), ("lift", LOW)]
        assert modal.calls == [("press", LOW), ("lift", LOW)]


class TestLettingEveryKeyGo:
    """Letting every key go lifts each held key once, through the scope that took it."""

    def test_every_held_key_is_lifted_by_its_taker(self, router: MidiRouter) -> None:
        panel, panel_switch = _scope(router, priority=PANEL, on=True)
        modal, modal_switch = _scope(router, priority=MODAL, on=False)
        router.publish()
        router.route(MidiNoteOn(note=LOW, velocity=VELOCITY))
        modal_switch.on, panel_switch.on = True, False
        router.publish()
        router.route(MidiNoteOn(note=HIGH, velocity=VELOCITY))

        router.route(MidiAllNotesOff())
        router.route(MidiNoteOff(note=LOW))

        assert panel.calls == [("press", LOW), ("lift", LOW)]
        assert modal.calls == [("press", HIGH), ("lift", HIGH)]

    def test_with_no_key_held_nothing_is_lifted(self, router: MidiRouter) -> None:
        panel, _ = _scope(router, priority=PANEL, on=True)
        router.publish()

        router.route(MidiAllNotesOff())

        assert panel.calls == []


class TestThePedal:
    """The sustain pedal reaches its one target whichever scope is active, and none at all."""

    def test_the_pedal_reaches_its_target_with_no_scope_active(self, router: MidiRouter) -> None:
        pedal: List[bool] = []
        router.take_pedal(pedal.append)
        router.publish()

        router.route(MidiPedal(down=True))
        router.route(MidiPedal(down=False))

        assert pedal == [True, False]

    def test_the_pedal_reaches_no_scope(self, router: MidiRouter) -> None:
        panel, _ = _scope(router, priority=PANEL, on=True)
        router.publish()

        router.route(MidiPedal(down=True))

        assert panel.calls == []
