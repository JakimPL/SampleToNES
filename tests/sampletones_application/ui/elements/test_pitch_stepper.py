from typing import Any, Dict, List, Tuple

import pytest

from sampletones_application.layout.general import PitchStepperLayout
from sampletones_application.ui.elements import pitch_stepper as pitch_stepper_module
from sampletones_application.ui.elements.pitch_stepper import GUIPitchStepper
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.constants.general import MAX_PERIOD, MAX_PITCH, MIN_PITCH
from sampletones_core.utils.pitch_kind import PERIOD, PITCH, PitchValueKind

LAYOUT = PitchStepperLayout(
    label_width=160,
    value_width=28,
    button_column_width=32,
    button_width=30,
    hold_delay=0.075,
    commit_delay=12,
)


class _ValueRecorder:
    """Captures the latest value the widget rendered for each widget tag."""

    def __init__(self) -> None:
        self.values: Dict[Any, Any] = {}

    def __call__(self, tag: Any, value: Any, *args: Any, **kwargs: Any) -> None:
        self.values[tag] = value


class _ScheduledEmits:
    """Stands in for ``CallbackQueue.add``, holding the debounced emits the widget scheduled until a test
    drains them, which mirrors the frame delay elapsing without a running queue."""

    def __init__(self) -> None:
        self.pending: List[Tuple[Any, Tuple[Any, ...]]] = []

    def __call__(self, callback: Any, *args: Any, **kwargs: Any) -> None:
        self.pending.append((callback, args))

    def flush(self) -> None:
        for callback, args in self.pending:
            callback(*args)
        self.pending.clear()


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _ValueRecorder:
    instance = _ValueRecorder()
    monkeypatch.setattr(pitch_stepper_module, "dpg_set_value", instance)
    return instance


@pytest.fixture(autouse=True)
def scheduled(monkeypatch: pytest.MonkeyPatch) -> _ScheduledEmits:
    instance = _ScheduledEmits()
    monkeypatch.setattr(CallbackQueue, "add", instance)
    return instance


def _stepper(*, kind: PitchValueKind, value: int) -> GUIPitchStepper:
    """A stepper carrying only the state the tested methods touch, bypassing the DearPyGui-dependent
    constructor."""
    stepper = GUIPitchStepper.__new__(GUIPitchStepper)
    stepper.on_value_changed = None
    stepper._kind = kind
    stepper._layout = LAYOUT
    stepper._value = kind.clamp(value)
    stepper._hold_direction = None
    stepper._hold_timer = None
    stepper._emit_token = 0
    stepper._input_tag = "stepper.input"
    stepper._value_tag = "stepper.input.text"
    return stepper


def _listen(stepper: GUIPitchStepper) -> List[int]:
    reported: List[int] = []
    stepper.on_value_changed = reported.append
    return reported


class TestSetValue:
    def test_clamps_into_range(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        stepper.set_value(MAX_PITCH + 50)
        assert stepper.value == MAX_PITCH

    def test_renders_note_name_and_readout(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        stepper.set_value(72)
        assert recorder.values[stepper._input_tag] == PITCH.to_name(72)
        assert recorder.values[stepper._value_tag] == "72"

    def test_does_not_report_change(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        reported = _listen(stepper)
        stepper.set_value(72)
        assert reported == []


class TestStep:
    def test_increment_reports_new_value(self, recorder: _ValueRecorder, scheduled: _ScheduledEmits) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        reported = _listen(stepper)
        stepper._step(1)
        assert stepper.value == 61
        scheduled.flush()
        assert reported == [61]

    def test_decrement_reports_new_value(self, recorder: _ValueRecorder, scheduled: _ScheduledEmits) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        reported = _listen(stepper)
        stepper._step(-1)
        scheduled.flush()
        assert reported == [59]

    def test_increment_clamps_at_maximum(self, recorder: _ValueRecorder, scheduled: _ScheduledEmits) -> None:
        stepper = _stepper(kind=PERIOD, value=MAX_PERIOD)
        reported = _listen(stepper)
        stepper._step(1)
        assert stepper.value == MAX_PERIOD
        scheduled.flush()
        assert reported == [MAX_PERIOD]

    def test_decrement_clamps_at_minimum(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=MIN_PITCH)
        stepper._step(-1)
        assert stepper.value == MIN_PITCH


class TestApplyText:
    def test_integer_text_is_clamped(self, recorder: _ValueRecorder, scheduled: _ScheduledEmits) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        reported = _listen(stepper)
        stepper._apply_text("9999")
        assert stepper.value == MAX_PITCH
        scheduled.flush()
        assert reported == [MAX_PITCH]

    def test_note_name_resolves(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        stepper._apply_text("C-3")
        assert stepper.value == PITCH.sanitized_name_to_value["C-3"]

    def test_garbage_falls_back_to_current(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=55)
        stepper._apply_text("not a note")
        assert stepper.value == 55

    def test_period_hex_name_resolves(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PERIOD, value=0)
        stepper._apply_text("A-#")
        assert stepper.value == 10


class TestDebounce:
    """A burst of steps renders each move immediately but reports the value once, after editing settles."""

    def test_steps_do_not_report_until_settled(self, recorder: _ValueRecorder, scheduled: _ScheduledEmits) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        reported = _listen(stepper)
        stepper._step(1)
        stepper._step(1)
        stepper._step(1)
        assert reported == []

    def test_burst_reports_final_value_once(self, recorder: _ValueRecorder, scheduled: _ScheduledEmits) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        reported = _listen(stepper)
        stepper._step(1)
        stepper._step(1)
        stepper._step(1)
        scheduled.flush()
        assert reported == [63]

    def test_superseded_emit_is_dropped(self, recorder: _ValueRecorder, scheduled: _ScheduledEmits) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        reported = _listen(stepper)
        stepper._step(1)
        stale_callback, stale_args = scheduled.pending[0]
        stepper._step(1)
        stale_callback(*stale_args)
        assert reported == []


class TestHoldTimer:
    def test_first_press_arms_timer_without_stepping(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        assert stepper._update_hold_timer(False, True, 0.0) is None
        assert stepper._hold_timer is not None

    def test_repeats_once_the_delay_elapses(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        stepper._update_hold_timer(False, True, 0.0)
        stepper._hold_timer = 0.0
        assert stepper._update_hold_timer(False, True, 0.01) == 1

    def test_no_button_pressed_returns_none(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        assert stepper._update_hold_timer(False, False, 0.05) is None

    def test_release_clears_hold_state(self, recorder: _ValueRecorder) -> None:
        stepper = _stepper(kind=PITCH, value=60)
        stepper._update_hold_timer(True, False, 0.0)
        stepper._on_mouse_release(0, None, None)
        assert stepper._hold_timer is None
        assert stepper._hold_direction is None
