from __future__ import annotations

from dataclasses import dataclass

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.general.colors.feature import FeatureColors
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.parameters.geometry import TabGeometry
from sampletones_application.ui.elements.pitch_stepper import PitchStepperStyle
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.utils.palette.colors.base import BaseColor


@dataclass(frozen=True)
class ReconstructionTabParameters:
    """Everything the Reconstruction tab coordinator needs, shaped for the coordinator.

    Geometry is flattened to the scalars the responsive sinks consume; the instruments
    panel's slice of the general layout is narrowed to a ``PitchStepperStyle`` plus the two
    extra fields it draws with, so the whole ``GeneralLayout`` never reaches a panel.
    """

    geometry: TabGeometry
    right_column_width: int
    right_column_height: int
    graphs: GraphsLayout
    pitch_stepper_style: PitchStepperStyle
    copy_width: int
    feature_colors: FeatureColors
    path_colors: PathColors
    path_status_color: BaseColor
    tree_colors: TreeColors
    scheduling: SchedulingBehavior

    @classmethod
    def from_config(cls, config: LayoutConfig) -> ReconstructionTabParameters:
        general = config.general
        return cls(
            geometry=TabGeometry.from_config(config),
            right_column_width=config.tabs.reconstruction.right_column.width,
            right_column_height=config.tabs.reconstruction.right_column.height,
            graphs=config.graphs,
            pitch_stepper_style=PitchStepperStyle.from_general(general),
            copy_width=general.buttons.copy_width,
            feature_colors=general.colors.features,
            path_colors=general.colors.paths,
            path_status_color=general.colors.text.disabled,
            tree_colors=TreeColors.create(
                general.colors,
                accent=general.colors.headers.reconstruction,
            ),
            scheduling=config.behavior.scheduling,
        )
