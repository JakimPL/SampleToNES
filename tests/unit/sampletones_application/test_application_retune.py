from typing import List, Optional
from unittest.mock import MagicMock

from sampletones_application.application import Application
from sampletones_application.services.result import ServiceCancelled
from sampletones_application.services.retune import RetunedSample


def _retuned(sample_id: str, rate: int) -> RetunedSample:
    reconstruction = MagicMock()
    reconstruction.config.nes_frequency = rate
    return RetunedSample(sample_id=sample_id, reconstruction=reconstruction)


def _app(
    current_rate: int,
    sample: Optional[MagicMock],
    open_reconstruction: Optional[MagicMock] = None,
) -> Application:
    app = Application.__new__(Application)
    app.project_manager = MagicMock()
    app.project_manager.current.settings.nes_frequency = current_rate
    app.project_manager.current.samples.get.return_value = sample
    app.reconstruction_manager = MagicMock()
    app.reconstruction_manager.reconstruction = open_reconstruction
    app.history = MagicMock()
    app.project_controller = MagicMock()
    app._sequencer_tab = MagicMock()
    app._reconstructions_tab = MagicMock()
    return app


class TestApplyRetunedSample:
    def test_swaps_the_reconstruction_when_the_rate_matches(self) -> None:
        app = _app(current_rate=60, sample=MagicMock())
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app.project_controller.replace_sample_reconstruction.assert_called_once_with("lead", retuned.reconstruction)

    def test_discards_a_stale_result_from_a_superseded_rate(self) -> None:
        app = _app(current_rate=30, sample=MagicMock())
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app.project_controller.replace_sample_reconstruction.assert_not_called()

    def test_ignores_a_removed_sample(self) -> None:
        app = _app(current_rate=60, sample=None)
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app.project_controller.replace_sample_reconstruction.assert_not_called()

    def test_rebinds_the_open_editor_when_it_shows_the_sample(self) -> None:
        open_reconstruction = MagicMock()
        sample = MagicMock()
        sample.reconstruction = open_reconstruction
        app = _app(current_rate=60, sample=sample, open_reconstruction=open_reconstruction)
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app.reconstruction_manager.apply_edited.assert_called_once_with(retuned.reconstruction)
        app._reconstructions_tab.update_reconstruction.assert_called_once()

    def test_leaves_the_editor_alone_when_a_different_sample_is_open(self) -> None:
        sample = MagicMock()
        sample.reconstruction = MagicMock()
        app = _app(current_rate=60, sample=sample, open_reconstruction=MagicMock())
        retuned = _retuned("lead", 60)

        app._apply_retuned_sample(retuned)

        app.reconstruction_manager.apply_edited.assert_not_called()
        app._reconstructions_tab.update_reconstruction.assert_not_called()


def _sample(sample_id: str, rate: int) -> MagicMock:
    sample = MagicMock()
    sample.id = sample_id
    sample.reconstruction.config.nes_frequency = rate
    return sample


def _app_for_rate(
    samples: List[MagicMock],
    open_reconstruction: Optional[MagicMock],
    running: bool = False,
) -> Application:
    app = Application.__new__(Application)
    app.project_manager = MagicMock()
    app.project_manager.current.samples = samples
    app.reconstruction_manager = MagicMock()
    app.reconstruction_manager.reconstruction = open_reconstruction
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
            open_reconstruction=open_sample.reconstruction,
        )

        app._retune_samples_for_rate(60)

        app._reconstructions_tab.set_reconstruction_dimmed.assert_called_once_with(True)

    def test_does_not_dim_when_the_open_sample_already_matches(self) -> None:
        open_sample = _sample("open", 60)
        app = _app_for_rate(
            [open_sample, _sample("other", 30)],
            open_reconstruction=open_sample.reconstruction,
        )

        app._retune_samples_for_rate(60)

        app._reconstructions_tab.set_reconstruction_dimmed.assert_not_called()

    def test_does_not_dim_when_no_reconstruction_is_open(self) -> None:
        app = _app_for_rate([_sample("a", 30), _sample("b", 30)], open_reconstruction=None)

        app._retune_samples_for_rate(60)

        app._reconstructions_tab.set_reconstruction_dimmed.assert_not_called()

    def test_restores_the_dim_when_the_batch_finishes(self) -> None:
        app = _app_for_rate([], open_reconstruction=None, running=False)

        app._on_retune_result(ServiceCancelled())

        app._reconstructions_tab.set_reconstruction_dimmed.assert_called_once_with(False)

    def test_keeps_the_dim_while_the_batch_is_running(self) -> None:
        app = _app_for_rate([], open_reconstruction=None, running=True)

        app._on_retune_result(ServiceCancelled())

        app._reconstructions_tab.set_reconstruction_dimmed.assert_not_called()
