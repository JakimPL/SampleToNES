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
from sampletones_application.utils.palette import PALETTE_CONTEXT_KEY, Palette
from sampletones_shared.utils.serialization import load_yaml_model, load_yaml_model_dir


def load_layout_config(layout_directory: Path, behavior_directory: Path, palette: Palette) -> LayoutConfig:
    context = {PALETTE_CONTEXT_KEY: palette}
    return LayoutConfig(
        general=load_yaml_model_dir(layout_directory / "general", GeneralLayout, context=context),
        fonts=load_yaml_model(layout_directory / "fonts.yaml", FontsLayout, context=context),
        glyphs=load_yaml_model(layout_directory / "glyphs.yaml", Glyphs, context=context),
        graphs=load_yaml_model_dir(layout_directory / "graphs", GraphsLayout, context=context),
        instructions=load_yaml_model_dir(layout_directory / "instructions", InstructionsLayout, context=context),
        main=load_yaml_model_dir(layout_directory / "main", MainLayout, context=context),
        player=load_yaml_model_dir(layout_directory / "player", PlayerLayout, context=context),
        project_properties=load_yaml_model_dir(
            layout_directory / "project_properties", ProjectPropertiesLayout, context=context
        ),
        sequencer=load_yaml_model_dir(layout_directory / "sequencer", SequencerLayout, context=context),
        settings=load_yaml_model_dir(layout_directory / "settings", SettingsLayout, context=context),
        behavior=load_yaml_model(behavior_directory / "general.yaml", BehaviorConfig, context=context),
    )
