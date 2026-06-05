from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel

from sampletones_application.layout.behavior import BehaviorConfig
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.instructions import InstructionsLayout
from sampletones_application.layout.main import MainLayout
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.reconstructions import ReconstructionsLayout
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.layout.settings import SettingsLayout
from sampletones_shared.utils.serialization import load_yaml

M = TypeVar("M", bound=BaseModel)


def _load(path: Path, model: Type[M]) -> M:
    raw = load_yaml(path)
    if not isinstance(raw, dict):
        raise TypeError(f"Layout file {path} must contain a mapping, got {type(raw)}")

    return model.model_validate(raw)


def load_layout_config(layout_directory: Path, behavior_directory: Path) -> LayoutConfig:
    return LayoutConfig(
        general=_load(layout_directory / "general.yaml", GeneralLayout),
        graphs=_load(layout_directory / "graphs.yaml", GraphsLayout),
        instructions=_load(layout_directory / "instructions.yaml", InstructionsLayout),
        main=_load(layout_directory / "main.yaml", MainLayout),
        player=_load(layout_directory / "player.yaml", PlayerLayout),
        reconstructions=_load(layout_directory / "reconstructions.yaml", ReconstructionsLayout),
        sequencer=_load(layout_directory / "sequencer.yaml", SequencerLayout),
        settings=_load(layout_directory / "settings.yaml", SettingsLayout),
        behavior=_load(behavior_directory / "general.yaml", BehaviorConfig),
    )
