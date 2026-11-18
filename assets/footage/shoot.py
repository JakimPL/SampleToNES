import hashlib
from pathlib import Path
from typing import Dict, Final, Mapping, Optional

from pydantic import BaseModel, ConfigDict

from assets.footage.schedule import Schedule
from assets.footage.shot import Shot

TAKE_VARIABLE: Final[str] = "SAMPLETONES_FOOTAGE_TAKE"


class MissingTakeError(LookupError):
    """Raised when a filming scene runs with no take handed over, as it does outside the footage maker."""


class Shoot(BaseModel):
    """What a footage's frames are filmed from, so frames filmed for one shoot are kept for the same shoot.

    Attributes:
        document: The reconstruction the application opens, or ``None`` for the demo piece in the scene's home.
        digest: The SHA-256 of the document's bytes, which changes with every conversion.
        tick_length: How many samples one tick of the document spans.
        stem_keys: The Stems card row of each named recording of the document, under the recording's name.
        schedule: The tick and the listening each frame is filmed at.
        shot: How the tab is framed.
    """

    model_config = ConfigDict(frozen=True)

    document: Optional[Path]
    digest: str
    tick_length: int
    stem_keys: Dict[str, str]
    schedule: Schedule
    shot: Shot


class Take(BaseModel):
    """One run of the filming scene: the shoot, the folder its frames are kept in, and the frame it stops before."""

    model_config = ConfigDict(frozen=True)

    shoot: Shoot
    frames: Path
    stop: int


def digest(path: Path) -> str:
    """The SHA-256 of the bytes at ``path``."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def take_environment(take: Take) -> Dict[str, str]:
    """The environment variable handing ``take`` to the scene's process."""
    return {TAKE_VARIABLE: take.model_dump_json()}


def handed_take(environment: Mapping[str, str]) -> Take:
    """The take the footage maker handed over through ``environment``.

    Raises:
        MissingTakeError: If no take was handed over.
    """
    if TAKE_VARIABLE not in environment:
        raise MissingTakeError(f"No take in {TAKE_VARIABLE}; python -m assets.footage films the scenes")

    return Take.model_validate_json(environment[TAKE_VARIABLE])
