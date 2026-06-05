from unittest.mock import MagicMock, patch

from sampletones_application.services.conversion import ConversionService
from sampletones_core.configs import Config


class TestConversionServiceArgumentRouting:
    """Verify that ConversionService.start() routes Config and Path arguments to
    ReconstructionConverter correctly, including deriving is_file from real filesystem state.

    ReconstructionConverter itself is still patched — running a real conversion requires WAV
    files and a process pool. The integration value here is that input_path.is_file() is
    evaluated against a real filesystem path (via tmp_path), not a MagicMock.
    """

    def _start_with_captured_kwargs(self, config: Config, path) -> dict:
        with patch("sampletones_application.services.conversion.ReconstructionConverter") as mock_cls:
            mock_cls.return_value = MagicMock()
            ConversionService().start(config, path)
        return mock_cls.call_args.kwargs

    def test_start_passes_is_file_true_for_regular_file(self, tmp_path, default_config) -> None:
        real_file = tmp_path / "sample.wav"
        real_file.write_bytes(b"")

        call_kwargs = self._start_with_captured_kwargs(default_config, real_file)

        assert call_kwargs["is_file"] is True

    def test_start_passes_is_file_false_for_directory(self, tmp_path, default_config) -> None:
        real_dir = tmp_path / "samples"
        real_dir.mkdir()

        call_kwargs = self._start_with_captured_kwargs(default_config, real_dir)

        assert call_kwargs["is_file"] is False

    def test_start_passes_config_to_converter(self, tmp_path, default_config) -> None:
        real_file = tmp_path / "sample.wav"
        real_file.write_bytes(b"")

        call_kwargs = self._start_with_captured_kwargs(default_config, real_file)

        assert call_kwargs["config"] is default_config

    def test_start_passes_input_path_to_converter(self, tmp_path, default_config) -> None:
        real_file = tmp_path / "sample.wav"
        real_file.write_bytes(b"")

        call_kwargs = self._start_with_captured_kwargs(default_config, real_file)

        assert call_kwargs["input_path"] == real_file
