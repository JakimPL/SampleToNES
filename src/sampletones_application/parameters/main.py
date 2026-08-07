from __future__ import annotations

from dataclasses import dataclass

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.tabs.main import MainLayout
from sampletones_application.parameters.geometry import TabGeometry
from sampletones_application.ui.elements.tree.colors import TreeColors


@dataclass(frozen=True)
class MainTabParameters:
    """Everything the Main tab coordinator needs, shaped for the coordinator.

    Assembled at the composition root from the validated storage config so the
    coordinator receives its own view instead of the whole ``LayoutConfig`` to
    disassemble. Geometry is flattened; cohesive feature models are forwarded whole.
    """

    geometry: TabGeometry
    config_height: int
    main: MainLayout
    inputs: InputsLayout
    path_colors: PathColors
    tree_colors: TreeColors
    scheduling: SchedulingBehavior

    @classmethod
    def from_config(cls, config: LayoutConfig) -> MainTabParameters:
        general = config.general
        return cls(
            geometry=TabGeometry.from_config(config),
            config_height=config.tabs.main.config.height,
            main=config.tabs.main,
            inputs=general.inputs,
            path_colors=general.colors.paths,
            tree_colors=TreeColors.create(
                general.colors,
                accent=general.colors.paths.hover,
            ),
            scheduling=config.behavior.scheduling,
        )
