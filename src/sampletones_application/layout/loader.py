from pathlib import Path

from sampletones_application.layout.behavior import BehaviorConfig
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.fonts import FontsLayout
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.glyphs import Glyphs
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.instructions import InstructionsLayout
from sampletones_application.layout.main import MainLayout
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.project_properties import ProjectPropertiesLayout
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.layout.settings import SettingsLayout
from sampletones_shared.utils.serialization import load_yaml_model


def load_layout_config(layout_directory: Path, behavior_directory: Path) -> LayoutConfig:
    return LayoutConfig(
        general=load_yaml_model(layout_directory / "general.yaml", GeneralLayout),
        fonts=load_yaml_model(layout_directory / "fonts.yaml", FontsLayout),
        glyphs=load_yaml_model(layout_directory / "glyphs.yaml", Glyphs),
        graphs=load_yaml_model(layout_directory / "graphs.yaml", GraphsLayout),
        instructions=load_yaml_model(layout_directory / "instructions.yaml", InstructionsLayout),
        main=load_yaml_model(layout_directory / "main.yaml", MainLayout),
        player=load_yaml_model(layout_directory / "player.yaml", PlayerLayout),
        project_properties=load_yaml_model(layout_directory / "project_properties.yaml", ProjectPropertiesLayout),
        sequencer=load_yaml_model(layout_directory / "sequencer.yaml", SequencerLayout),
        settings=load_yaml_model(layout_directory / "settings.yaml", SettingsLayout),
        behavior=load_yaml_model(behavior_directory / "general.yaml", BehaviorConfig),
    )
