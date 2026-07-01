from enum import StrEnum
from typing import FrozenSet

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class ReconstructionPathState(StrEnum):
    """Whether a path can be shown for a reconstruction location.

    ``AVAILABLE`` carries a resolvable path. ``NOT_FOUND`` marks a recorded path whose
    file is absent on this machine. ``NOT_APPLICABLE`` marks a location that a
    reconstruction does not have (a sequencer sample keeps no file locations).
    ``EMPTY`` is the resting state when no reconstruction is loaded.
    """

    AVAILABLE = "available"
    NOT_FOUND = "not_found"
    NOT_APPLICABLE = "not_applicable"
    EMPTY = "empty"


class ReconstructionPathViewModel(BaseModel, frozen=True):
    state: ReconstructionPathState
    path: str


class ReconstructionViewModel(BaseModel, frozen=True):
    reconstruction_loaded: bool
    available_generators: FrozenSet[GeneratorName]
    audio_source_enabled: bool
    buttons_enabled: bool
    reconstruction_file: ReconstructionPathViewModel
    original_audio: ReconstructionPathViewModel
