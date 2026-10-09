from typing import Final, List, Optional
from unittest.mock import MagicMock

from sampletones_application.application import Application
from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.reconstruction.edit import Retune
from sampletones_application.logic.reconstruction.rewrites.steps import RateChange
from sampletones_application.services.result import ServiceCanceled
from sampletones_application.services.retune import RetunedSample
from sampletones_core.project.voices.sample import Sample

OPEN_VOICE_ID: Final[str] = "open"
RATE: Final[int] = 60


def _sample_double() -> Sample:
    """A real project sample over a stand-in reconstruction, since the routing tells the kinds apart."""
    return Sample(name="lead", reconstruction=MagicMock())


def _retuned(voice_id: str, rate: int, source: MagicMock) -> RetunedSample:
    reconstruction = MagicMock()
    reconstruction.config.nes_frequency = rate
    return RetunedSample(voice_id=voice_id, reconstruction=reconstruction, source=source)


def _app(
    current_rate: int,
    sample: Optional[Sample],
    *,
    open_voice_id: Optional[str],
) -> Application:
    app = Application.__new__(Application)
    app.project_manager = MagicMock()
    app.project_manager.current.settings.nes_frequency = current_rate
    app.project_manager.current.voices.get.return_value = sample
    app.reconstruction_manager = MagicMock()
    app.reconstruction_manager.voice_id = open_voice_id
    app.history = MagicMock()
    app.project_controller = MagicMock()
    app._sequencer_tab = MagicMock()
    app._reconstruction_coordinator = MagicMock(spec=ReconstructionCoordinator)
    return app


class TestApplyRetunedSample:
    def test_swaps_the_reconstruction_when_the_rate_matches(self) -> None:
        sample = _sample_double()
        app = _app(current_rate=RATE, sample=sample, open_voice_id=None)
        retuned = _retuned("lead", RATE, source=sample.reconstruction)

        app._apply_retuned_sample(retuned)

        app.project_controller.replace_sample_reconstruction.assert_called_once_with("lead", retuned.reconstruction)

    def test_discards_a_stale_result_from_a_superseded_rate(self) -> None:
        sample = _sample_double()
        app = _app(current_rate=30, sample=sample, open_voice_id=None)

        app._apply_retuned_sample(_retuned("lead", RATE, source=sample.reconstruction))

        app.project_controller.replace_sample_reconstruction.assert_not_called()

    def test_ignores_a_removed_sample(self) -> None:
        app = _app(current_rate=RATE, sample=None, open_voice_id=None)

        app._apply_retuned_sample(_retuned("lead", RATE, source=MagicMock()))

        app.project_controller.replace_sample_reconstruction.assert_not_called()

    def test_folds_the_retune_into_the_rate_change_entry(self) -> None:
        sample = _sample_double()
        app = _app(current_rate=RATE, sample=sample, open_voice_id=None)

        app._apply_retuned_sample(_retuned("lead", RATE, source=sample.reconstruction))

        action = app.history.transaction.call_args.args[0]
        assert action is HistoryAction.SET_NES_FREQUENCY
        assert app.history.transaction.call_args.kwargs["coalesce"] == (RATE,)

    def test_a_sample_opened_since_the_batch_started_takes_the_rate_as_a_step(self) -> None:
        """The open document changes one step at a time, so the rate waits for the edits made there."""
        sample = _sample_double()
        app = _app(current_rate=RATE, sample=sample, open_voice_id=sample.id)

        app._apply_retuned_sample(_retuned(sample.id, RATE, source=sample.reconstruction))

        app._reconstruction_coordinator.request_rewrite.assert_called_once_with(RateChange(nes_frequency=RATE))
        app.project_controller.replace_sample_reconstruction.assert_not_called()

    def test_another_samples_retune_leaves_the_open_document_alone(self) -> None:
        sample = _sample_double()
        app = _app(current_rate=RATE, sample=sample, open_voice_id=OPEN_VOICE_ID)

        app._apply_retuned_sample(_retuned("lead", RATE, source=sample.reconstruction))

        app._reconstruction_coordinator.request_rewrite.assert_not_called()

    def test_a_discarded_result_reaches_no_document(self) -> None:
        sample = _sample_double()
        app = _app(current_rate=30, sample=sample, open_voice_id=sample.id)

        app._apply_retuned_sample(_retuned(sample.id, RATE, source=sample.reconstruction))

        app._reconstruction_coordinator.request_rewrite.assert_not_called()


class TestASampleChangedSinceTheBatchStarted:
    """A batch retunes what each sample held as it started, so a sample edited since is retuned afresh."""

    def test_it_is_retuned_from_what_it_now_holds(self) -> None:
        sample = _sample_double()
        app = _app(current_rate=RATE, sample=sample, open_voice_id=None)

        app._apply_retuned_sample(_retuned("lead", RATE, source=MagicMock()))

        app.project_controller.replace_sample_reconstruction.assert_called_once_with(
            "lead",
            sample.reconstruction.with_nes_frequency.return_value,
        )

    def test_a_sample_already_at_the_rate_is_left_as_it_is(self) -> None:
        sample = _sample_double()
        sample.reconstruction.with_nes_frequency.return_value = sample.reconstruction
        app = _app(current_rate=RATE, sample=sample, open_voice_id=None)

        app._apply_retuned_sample(_retuned("lead", RATE, source=MagicMock()))

        app.project_controller.replace_sample_reconstruction.assert_not_called()


def _sample(voice_id: str, rate: int) -> Sample:
    sample = _sample_double()
    sample.id = voice_id
    sample.reconstruction.config.nes_frequency = rate
    return sample


def _app_for_rate(
    samples: List[Sample],
    open_sample: Optional[Sample],
    running: bool = False,
) -> Application:
    app = Application.__new__(Application)
    app.project_manager = MagicMock()
    app.project_manager.current.voices = samples
    app.project_manager.current.voice.side_effect = {sample.id: sample for sample in samples}.get
    app.reconstruction_manager = MagicMock()
    app.reconstruction_manager.voice_id = None if open_sample is None else open_sample.id
    app.retune_service = MagicMock()
    app.retune_service.start.return_value = True
    app.retune_service.is_running.return_value = running
    app.status_bar = MagicMock()
    app.language_manager = MagicMock()
    app._reconstructions_tab = MagicMock()
    app._reconstruction_coordinator = MagicMock(spec=ReconstructionCoordinator)
    return app


class TestTheOpenSampleTakesTheRateAsAStep:
    """The sample open on the Reconstructions tab is re-timed as a step of its document, after the edits made there."""

    def test_the_open_sample_asks_for_the_rate(self) -> None:
        open_sample = _sample(OPEN_VOICE_ID, 30)
        app = _app_for_rate([open_sample, _sample("other", 30)], open_sample=open_sample)

        app._retune_samples_for_rate(RATE)

        app._reconstruction_coordinator.request_rewrite.assert_called_once_with(RateChange(nes_frequency=RATE))

    def test_the_open_sample_is_left_out_of_the_batch(self) -> None:
        open_sample = _sample(OPEN_VOICE_ID, 30)
        other = _sample("other", 30)
        app = _app_for_rate([open_sample, other], open_sample=open_sample)

        app._retune_samples_for_rate(RATE)

        targets, rate = app.retune_service.start.call_args.args
        assert [voice_id for voice_id, _reconstruction in targets] == [other.id]
        assert rate == RATE

    def test_no_sample_open_asks_for_no_step(self) -> None:
        app = _app_for_rate([_sample("a", 30), _sample("b", 30)], open_sample=None)

        app._retune_samples_for_rate(RATE)

        app._reconstruction_coordinator.request_rewrite.assert_not_called()
        assert len(app.retune_service.start.call_args.args[0]) == 2

    def test_the_status_clears_when_the_batch_finishes(self) -> None:
        app = _app_for_rate([], open_sample=None, running=False)

        app._on_retune_result(ServiceCanceled())

        app.status_bar.set.assert_called_once_with("")

    def test_the_status_stands_while_the_batch_is_running(self) -> None:
        app = _app_for_rate([], open_sample=None, running=True)

        app._on_retune_result(ServiceCanceled())

        app.status_bar.set.assert_not_called()


class TestARetuneOfTheOpenSampleIsRecorded:
    """A retune landing on the open sample joins the rate change it follows."""

    def test_it_is_recorded_as_the_rate_change(self) -> None:
        sample = _sample_double()
        app = _app(current_rate=RATE, sample=sample, open_voice_id=sample.id)
        app.project_manager.current.voice.return_value = sample
        retuned = MagicMock()

        app._on_reconstruction_updated(Retune(reconstruction=retuned, nes_frequency=RATE))

        transaction = app.history.transaction.call_args
        assert transaction.args[0] is HistoryAction.SET_NES_FREQUENCY
        assert transaction.kwargs["coalesce"] == (RATE,)
        assert transaction.kwargs["detail"] is app._sequencer_tab.nes_frequency_detail.return_value
        app._sequencer_tab.nes_frequency_detail.assert_called_once_with(RATE)
        app.project_controller.replace_sample_reconstruction.assert_called_once_with(sample.id, retuned)
