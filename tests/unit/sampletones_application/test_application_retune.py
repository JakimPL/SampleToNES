from typing import List, Optional
from unittest.mock import MagicMock

from sampletones_application.application import Application
from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.services.result import ServiceCanceled
from sampletones_application.services.retune import RetunedSample
from sampletones_core.project.voices.sample import Sample


def _sample_double() -> Sample:
    """A real project sample over a stand-in reconstruction, since the routing tells the kinds apart."""
    return Sample(name="lead", reconstruction=MagicMock())


def _retuned(voice_id: str, rate: int) -> RetunedSample:
    reconstruction = MagicMock()
    reconstruction.config.nes_frequency = rate
    return RetunedSample(voice_id=voice_id, reconstruction=reconstruction)


def _app(
    current_rate: int,
    sample: Optional[Sample],
) -> Application:
    app = Application.__new__(Application)
    app.project_manager = MagicMock()
    app.project_manager.current.settings.nes_frequency = current_rate
    app.project_manager.current.voices.get.return_value = sample
    app.history = MagicMock()
    app.project_controller = MagicMock()
    app._sequencer_tab = MagicMock()
    app._reconstruction_coordinator = MagicMock(spec=ReconstructionCoordinator)
    return app


class TestApplyRetunedSample:
    def test_swaps_the_reconstruction_when_the_rate_matches(self) -> None:
        app = _app(current_rate=60, sample=_sample_double())
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app.project_controller.replace_sample_reconstruction.assert_called_once_with("lead", retuned.reconstruction)

    def test_discards_a_stale_result_from_a_superseded_rate(self) -> None:
        app = _app(current_rate=30, sample=_sample_double())
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app.project_controller.replace_sample_reconstruction.assert_not_called()

    def test_ignores_a_removed_sample(self) -> None:
        app = _app(current_rate=60, sample=None)
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app.project_controller.replace_sample_reconstruction.assert_not_called()

    def test_hands_the_retuned_sample_to_the_open_document(self) -> None:
        """The document open on the Reconstructions tab decides whether it is the sample retuned."""
        app = _app(current_rate=60, sample=_sample_double())
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app._reconstruction_coordinator.retune_sample.assert_called_once_with("lead", retuned.reconstruction)

    def test_a_discarded_result_reaches_no_document(self) -> None:
        app = _app(current_rate=30, sample=_sample_double())

        app._apply_retuned_sample(_retuned("lead", 60))

        app._reconstruction_coordinator.retune_sample.assert_not_called()


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
    return app


class TestRetuneDim:
    def test_dims_the_open_reconstruction_when_it_will_be_retuned(self) -> None:
        open_sample = _sample("open", 30)
        app = _app_for_rate(
            [open_sample, _sample("other", 30)],
            open_sample=open_sample,
        )

        app._retune_samples_for_rate(60)

        app._reconstructions_tab.set_reconstruction_dimmed.assert_called_once_with(True)

    def test_does_not_dim_when_the_open_sample_already_matches(self) -> None:
        open_sample = _sample("open", 60)
        app = _app_for_rate(
            [open_sample, _sample("other", 30)],
            open_sample=open_sample,
        )

        app._retune_samples_for_rate(60)

        app._reconstructions_tab.set_reconstruction_dimmed.assert_not_called()

    def test_does_not_dim_when_no_reconstruction_is_open(self) -> None:
        app = _app_for_rate([_sample("a", 30), _sample("b", 30)], open_sample=None)

        app._retune_samples_for_rate(60)

        app._reconstructions_tab.set_reconstruction_dimmed.assert_not_called()

    def test_restores_the_dim_when_the_batch_finishes(self) -> None:
        app = _app_for_rate([], open_sample=None, running=False)

        app._on_retune_result(ServiceCanceled())

        app._reconstructions_tab.set_reconstruction_dimmed.assert_called_once_with(False)

    def test_keeps_the_dim_while_the_batch_is_running(self) -> None:
        app = _app_for_rate([], open_sample=None, running=True)

        app._on_retune_result(ServiceCanceled())

        app._reconstructions_tab.set_reconstruction_dimmed.assert_not_called()
