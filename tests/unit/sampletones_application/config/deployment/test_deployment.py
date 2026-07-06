from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from sampletones_application.config.deployment.deployment import (
    LOG_LEVEL_ENV,
    STRICT_HISTORY_ENV,
    DeploymentConfig,
)
from sampletones_application.config.deployment.logs import LogLevel


def _write_deployment(path: Path, *, log_level: str, strict_history: bool) -> Path:
    path.write_text(yaml.safe_dump({"log_level": log_level, "strict_history": strict_history}))
    return path


@pytest.fixture
def deployment_path(tmp_path: Path) -> Path:
    return _write_deployment(tmp_path / "deployment.yaml", log_level="WARNING", strict_history=True)


@pytest.fixture(autouse=True)
def _clear_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(LOG_LEVEL_ENV, raising=False)
    monkeypatch.delenv(STRICT_HISTORY_ENV, raising=False)


class TestDeploymentConfigFileBaseline:
    def test_uses_file_values_when_no_override_is_set(self, deployment_path: Path) -> None:
        config = DeploymentConfig.load(deployment_path)

        assert config.log_level is LogLevel.WARNING
        assert config.strict_history is True


class TestDeploymentConfigEnvironmentOverride:
    def test_log_level_override_wins_over_file(self, deployment_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(LOG_LEVEL_ENV, "DEBUG")

        config = DeploymentConfig.load(deployment_path)

        assert config.log_level is LogLevel.DEBUG
        assert config.strict_history is True

    def test_strict_history_override_wins_over_file(
        self, deployment_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(STRICT_HISTORY_ENV, "0")

        config = DeploymentConfig.load(deployment_path)

        assert config.strict_history is False
        assert config.log_level is LogLevel.WARNING

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("1", True),
            ("true", True),
            ("TRUE", True),
            ("yes", True),
            ("on", True),
            ("0", False),
            ("false", False),
            ("no", False),
            ("off", False),
        ],
    )
    def test_strict_history_boolean_coercion(
        self, deployment_path: Path, monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
    ) -> None:
        monkeypatch.setenv(STRICT_HISTORY_ENV, value)

        config = DeploymentConfig.load(deployment_path)

        assert config.strict_history is expected


class TestDeploymentConfigValidation:
    def test_invalid_override_log_level_raises(self, deployment_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(LOG_LEVEL_ENV, "NOPE")

        with pytest.raises(ValidationError):
            DeploymentConfig.load(deployment_path)

    @pytest.mark.parametrize("value", ["", "maybe", "2"])
    def test_invalid_override_strict_history_raises(
        self, deployment_path: Path, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv(STRICT_HISTORY_ENV, value)

        with pytest.raises(ValidationError):
            DeploymentConfig.load(deployment_path)

    def test_non_mapping_file_raises_type_error(self, tmp_path: Path) -> None:
        path = tmp_path / "deployment.yaml"
        path.write_text(yaml.safe_dump(["not", "a", "mapping"]))

        with pytest.raises(TypeError):
            DeploymentConfig.load(path)
