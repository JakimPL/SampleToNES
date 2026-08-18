from pathlib import Path

from sampletones_application.layout.behavior.behavior import BehaviorConfig
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.fonts import FontsLayout
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.glyphs.glyphs import Glyphs
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.project_properties import ProjectPropertiesLayout
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.layout.tabs import TabsLayout
from sampletones_application.layout.tabs.instructions import InstructionsLayout
from sampletones_application.layout.tabs.main import MainLayout
from sampletones_application.layout.tabs.reconstruction import ReconstructionLayout
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.utils.palette.colors.written import PALETTE_SOURCE_CONTEXT_KEY
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_shared.utils.serialization import load_yaml_model, load_yaml_model_dir


def load_layout_config(
    layout_directory: Path,
    behavior_directory: Path,
    palette_source: PaletteSource,
) -> LayoutConfig:
    context = {PALETTE_SOURCE_CONTEXT_KEY: palette_source}
    tabs_directory = layout_directory / "tabs"
    return LayoutConfig(
        general=load_yaml_model_dir(
            layout_directory / "general",
            GeneralLayout,
            context=context,
        ),
        fonts=load_yaml_model(
            layout_directory / "fonts.yaml",
            FontsLayout,
            context=context,
        ),
        glyphs=load_yaml_model(
            layout_directory / "glyphs.yaml",
            Glyphs,
            context=context,
        ),
        graphs=load_yaml_model_dir(
            layout_directory / "graphs",
            GraphsLayout,
            context=context,
        ),
        tabs=TabsLayout(
            main=load_yaml_model_dir(
                tabs_directory / "main",
                MainLayout,
                context=context,
            ),
            instructions=load_yaml_model_dir(
                tabs_directory / "instructions",
                InstructionsLayout,
                context=context,
            ),
            reconstruction=load_yaml_model_dir(
                tabs_directory / "reconstruction",
                ReconstructionLayout,
                context=context,
            ),
            sequencer=load_yaml_model_dir(
                tabs_directory / "sequencer",
                SequencerLayout,
                context=context,
            ),
        ),
        player=load_yaml_model_dir(
            layout_directory / "player",
            PlayerLayout,
            context=context,
        ),
        project_properties=load_yaml_model_dir(
            layout_directory / "project_properties",
            ProjectPropertiesLayout,
            context=context,
        ),
        settings=load_yaml_model_dir(
            layout_directory / "settings",
            SettingsLayout,
            context=context,
        ),
        behavior=load_yaml_model(
            behavior_directory / "general.yaml",
            BehaviorConfig,
            context=context,
        ),
    )
