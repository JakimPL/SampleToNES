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

    Every field is required, and ``deployment.yaml`` supplies the baseline. It carries the
    development values — verbose logging, and strict history so a missing transaction is
    reported the moment it happens rather than healed in silence — since the source tree is
    where an edit is written and where that report is worth having. A release build injects the
    user-facing values through ``scripts/release_env_hook.py``, so a shipped artifact is quiet
    and self-healing whatever the tree it was built from said.

    The ``SAMPLETONES_LOG_LEVEL`` and ``SAMPLETONES_STRICT_HISTORY`` environment variables set
    either field, which is how the release hook states its values and how a run of either kind
    takes the other's.
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
