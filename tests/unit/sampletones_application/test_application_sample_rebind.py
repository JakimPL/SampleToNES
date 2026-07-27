from typing import Optional
from unittest.mock import MagicMock

from sampletones_application.application import Application


def _app(
    sample: Optional[MagicMock],
    open_reconstruction: Optional[MagicMock],
) -> Application:
    app = Application.__new__(Application)
    app.project_manager = MagicMock()
    app.project_manager.current.sample.return_value = sample
    app.reconstruction_manager = MagicMock()
    app.reconstruction_manager.reconstruction = open_reconstruction
    app._reconstructions_tab = MagicMock()
    return app


class TestRebindReplacedSample:
    def test_rebinds_the_editor_showing_the_replaced_sample(self) -> None:
        outgoing = MagicMock()
        sample = MagicMock()
        sample.reconstruction = outgoing
        app = _app(sample=sample, open_reconstruction=outgoing)
        incoming = MagicMock()

        app._rebind_replaced_sample("bass-id", incoming)

        app.reconstruction_manager.apply_regenerated.assert_called_once_with(incoming)
        app._reconstructions_tab.update_reconstruction.assert_called_once()

    def test_leaves_the_editor_alone_when_a_different_sample_is_open(self) -> None:
        sample = MagicMock()
        sample.reconstruction = MagicMock()
        app = _app(sample=sample, open_reconstruction=MagicMock())

        app._rebind_replaced_sample("bass-id", MagicMock())

        app.reconstruction_manager.apply_regenerated.assert_not_called()
        app._reconstructions_tab.update_reconstruction.assert_not_called()

    def test_leaves_the_editor_alone_when_no_document_is_open(self) -> None:
        sample = MagicMock()
        sample.reconstruction = MagicMock()
        app = _app(sample=sample, open_reconstruction=None)

        app._rebind_replaced_sample("bass-id", MagicMock())

        app.reconstruction_manager.apply_regenerated.assert_not_called()
        app._reconstructions_tab.update_reconstruction.assert_not_called()

    def test_ignores_an_unknown_sample(self) -> None:
        app = _app(sample=None, open_reconstruction=MagicMock())

        app._rebind_replaced_sample("gone", MagicMock())

        app.reconstruction_manager.apply_regenerated.assert_not_called()
        app._reconstructions_tab.update_reconstruction.assert_not_called()
