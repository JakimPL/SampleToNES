from pathlib import Path
from typing import Final

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.history.transaction import CoalesceKey
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project import Project
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from tests.suite.history.audit import HistoryAudit, StackModel, immediately
from tests.suite.history.projects import FIRST_PATTERN, LEAD, PAD
from tests.unit.sampletones_application.logic.history.conftest import AUDIT_BUDGET, AuditedHistory

TEMPO_KEY: Final[CoalesceKey] = ("tempo",)
FIRST_ROW: Final[int] = 0
PLANTED_VOLUME: Final[int] = 1
PLANTED_PITCH: Final[int] = 30
UNHEARD_SAVE: Final[str] = "unheard.stp"


def _raise_tempo(audited: AuditedHistory) -> None:
    def gesture() -> None:
        with audited.history.transaction(HistoryAction.SET_TEMPO, coalesce=TEMPO_KEY):
            audited.controller.set_tempo(audited.controller.project.settings.tempo + 1)

    audited.audit.perform(gesture, action=HistoryAction.SET_TEMPO, target=TEMPO_KEY)


def _speed_up(audited: AuditedHistory) -> None:
    with audited.history.transaction(HistoryAction.SET_SPEED):
        audited.controller.set_speed(audited.controller.project.settings.speed + 1)


def _speed_up_audited(audited: AuditedHistory) -> None:
    audited.audit.perform(lambda: _speed_up(audited), action=HistoryAction.SET_SPEED, target=None)


def _retitle_audited(audited: AuditedHistory) -> None:
    def gesture() -> None:
        with audited.history.transaction(HistoryAction.EDIT_PROJECT_PROPERTIES):
            audited.controller.set_title(f"{audited.controller.project.info.title}!")

    audited.audit.perform(gesture, action=HistoryAction.EDIT_PROJECT_PROPERTIES, target=None)


def _sample(
    project: Project,
    name: str,
) -> Sample:
    return next(voice for voice in project.voices if isinstance(voice, Sample) and voice.name == name)


def _instrument(
    project: Project,
    name: str,
) -> Instrument:
    return next(voice for voice in project.voices if isinstance(voice, Instrument) and voice.name == name)


def _baseline(audited: AuditedHistory) -> Project:
    return audited.history.entries[0].project


class OvershootingDoors:
    """Doors whose undo lands on the first entry, as a history restoring the wrong entry would."""

    def __init__(self, history: HistoryManager) -> None:
        self._history = history

    def undo(self) -> None:
        self._history.jump_to(0)

    def redo(self) -> None:
        self._history.redo()

    def jump_to(self, index: int) -> None:
        self._history.jump_to(index)


class TestACleanHistoryPasses:
    def test_a_walk_over_recorded_gestures_holds(self, audited: AuditedHistory) -> None:
        _raise_tempo(audited)
        _speed_up_audited(audited)
        _retitle_audited(audited)

        audited.audit.walk()

        assert audited.audit.model.cursor == 3

    def test_a_run_of_one_target_holds(self, audited: AuditedHistory) -> None:
        _raise_tempo(audited)
        _raise_tempo(audited)

        audited.audit.walk()

        assert len(audited.history.entries) == 2


class TestPlantedFaults:
    """Each fault the history must never make, planted by hand, fails the audit's next check."""

    def test_a_row_changed_inside_an_entry(self, audited: AuditedHistory) -> None:
        _raise_tempo(audited)
        row = _baseline(audited).song.channels[ChannelName.PULSE1].get_row(FIRST_PATTERN, FIRST_ROW)

        object.__setattr__(row, "volume", PLANTED_VOLUME)

        with pytest.raises(AssertionError, match="Entry 0"):
            audited.audit.check()

    def test_a_shared_stream_changed_in_place(self, audited: AuditedHistory) -> None:
        _raise_tempo(audited)
        reconstruction = _sample(audited.controller.project, LEAD).reconstruction
        stream = reconstruction.instructions_data[0]

        object.__setattr__(stream, "initial_pitch", PLANTED_PITCH)

        with pytest.raises(AssertionError, match="Entry 0"):
            audited.audit.check()

    def test_an_envelope_changed_inside_an_entry(self, audited: AuditedHistory) -> None:
        _raise_tempo(audited)
        instrument = _instrument(_baseline(audited), PAD)

        object.__setattr__(instrument.envelopes, "volume", instrument.envelopes.arpeggio)

        with pytest.raises(AssertionError, match="Entry 0"):
            audited.audit.check()

    def test_a_restore_installing_another_entry(self, audited: AuditedHistory) -> None:
        overshooting = AuditedHistory(
            controller=audited.controller,
            history=audited.history,
            audit=HistoryAudit(
                audited.controller,
                audited.history,
                budget=AUDIT_BUDGET,
                doors=OvershootingDoors(audited.history),
                settle=immediately,
            ),
        )
        _raise_tempo(overshooting)
        _speed_up_audited(overshooting)

        with pytest.raises(AssertionError, match="cursor stands at 0"):
            overshooting.audit.undo()

    def test_a_live_project_another_entry_put_in_place(self, audited: AuditedHistory) -> None:
        _raise_tempo(audited)

        audited.controller.replace_project(_baseline(audited), clean=False)

        with pytest.raises(AssertionError, match="live project differs"):
            audited.audit.check()

    def test_a_gesture_recorded_under_another_action(self, audited: AuditedHistory) -> None:
        with pytest.raises(AssertionError, match="holds"):
            audited.audit.perform(
                lambda: _speed_up(audited),
                action=HistoryAction.SET_TEMPO,
                target=None,
            )

    def test_a_gesture_that_records_nothing(self, audited: AuditedHistory) -> None:
        with pytest.raises(AssertionError, match="left the project as it stood"):
            audited.audit.perform(lambda: None, action=HistoryAction.SET_TEMPO, target=None)

    def test_a_stale_reconstruction_view(self, audited: AuditedHistory) -> None:
        reconstruction = _sample(audited.controller.project, LEAD).reconstruction
        pitches = dict(reconstruction.initial_pitches)
        pitches[ChannelName.PULSE1] = PLANTED_PITCH

        vars(reconstruction)["initial_pitches"] = pitches

        with pytest.raises(AssertionError, match="stale initial_pitches"):
            audited.audit.check()

    def test_stale_instrument_frames(self, audited: AuditedHistory) -> None:
        instrument = _instrument(audited.controller.project, PAD)
        frames = instrument.instructions(ChannelName.PULSE1)

        vars(instrument)["_instructions"] = {channel: frames[:1] for channel in ChannelName.items()}

        with pytest.raises(AssertionError, match="stale pulse1 frames"):
            audited.audit.check()

    def test_a_voices_collection_that_lost_its_ids(self, audited: AuditedHistory) -> None:
        _raise_tempo(audited)
        baseline = _baseline(audited)

        baseline.voices = baseline.voices.copy()  # type: ignore[assignment]

        with pytest.raises(AssertionError, match="answers"):
            audited.audit.check()

    def test_a_save_the_history_never_heard_of(
        self,
        audited: AuditedHistory,
        tmp_path: Path,
    ) -> None:
        _raise_tempo(audited)
        audited.controller.on_saved = None

        audited.controller.save(tmp_path / UNHEARD_SAVE)

        with pytest.raises(AssertionError, match="reads clean"):
            audited.audit.check()


class TestTheModel:
    """The model's own rules, read against cases worked out by hand."""

    def test_a_commit_below_the_save_point_drops_it(self) -> None:
        model = StackModel(budget=10)
        model.reset("baseline", clean=True)
        model.commit(HistoryAction.SET_TEMPO, None, "tempo")
        model.save()
        model.undo()

        model.commit(HistoryAction.SET_SPEED, None, "speed")

        assert model.saved is None
        assert [entry.fingerprint for entry in model.entries] == ["baseline", "speed"]

    def test_eviction_takes_the_save_point_along(self) -> None:
        model = StackModel(budget=2)
        model.reset("baseline", clean=True)

        model.commit(HistoryAction.SET_TEMPO, None, "tempo")
        model.commit(HistoryAction.SET_SPEED, None, "speed")

        assert model.saved is None
        assert model.cursor == 1

    def test_a_restore_ends_a_run(self) -> None:
        model = StackModel(budget=10)
        model.reset("baseline", clean=True)
        model.commit(HistoryAction.SET_TEMPO, TEMPO_KEY, "first")
        model.undo()
        model.redo()

        model.commit(HistoryAction.SET_TEMPO, TEMPO_KEY, "second")

        assert [entry.fingerprint for entry in model.entries] == ["baseline", "first", "second"]
