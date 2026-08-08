from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from pydantic import BaseModel

from sampletones_application.config.deployment.logs import LogLevel
from sampletones_shared.application import SAMPLETONES_ENV_PREFIX
from sampletones_shared.utils.serialization import load_yaml


class DeploymentConfig(BaseModel, frozen=True):
    """Environment-level knobs decided at deployment time, not by the end user.

    ``strict_history`` turns an untracked domain mutation into an immediate
    ``UntrackedMutationError``, surfacing completeness gaps at once; with it off
    the history self-heals by recording the mutation as its own entry.
    ``log_level`` sets the verbosity of the application logger at startup.

    Every field is required, and the shipped ``deployment.yaml`` supplies the
    authoritative baseline for each one. The ``SAMPLETONES_LOG_LEVEL`` and
    ``SAMPLETONES_STRICT_HISTORY`` environment variables override individual
    fields when set, letting a development run raise verbosity or enable strict
    history while the shipped file keeps user builds quiet and self-healing.
    """

    log_level: LogLevel
    strict_history: bool

    @staticmethod
    def _environment_overrides() -> Dict[str, str]:
        return {
            field: value
            for field in DeploymentConfig.model_fields
            if (value := os.getenv(f"{SAMPLETONES_ENV_PREFIX}{field.upper()}"))
        }

    @classmethod
    def load(cls, deployment_path: Path) -> DeploymentConfig:
        raw = load_yaml(deployment_path)
        if not isinstance(raw, dict):
            raise TypeError(f"Deployment config {deployment_path} must contain a mapping, got {type(raw)}")

        return cls.model_validate({**raw, **cls._environment_overrides()})
