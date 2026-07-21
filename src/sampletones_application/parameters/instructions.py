from __future__ import annotations

from dataclasses import dataclass

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.general.colors import TableColors
from sampletones_application.layout.general.tables import TablesLayout
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.tabs.instructions import InstructionsLayout
from sampletones_application.parameters.geometry import TabGeometry
from sampletones_application.ui.elements.pitch_stepper import PitchStepperStyle
from sampletones_application.ui.elements.tree.colors import TreeColors


@dataclass(frozen=True)
class InstructionsTabParameters:
    """Everything the Instructions tab coordinator needs, shaped for the coordinator.

    The stacked-graph geometry — the vertical baseline, the per-graph base height, and the
    ceiling the stack grows to — is flattened alongside the shared column geometry because it
    feeds the ``stacked_graph_height`` pure-int sink; the choice panel's slice of the general
    layout is narrowed to a ``PitchStepperStyle`` so the whole ``GeneralLayout`` never reaches
    a panel.
    """

    geometry: TabGeometry
    baseline_viewport_height: int
    max_stack_height: int
    base_graph_height: int
    right_column_width: int
    right_column_height: int
    instructions: InstructionsLayout
    graphs: GraphsLayout
    pitch_stepper_style: PitchStepperStyle
    table_colors: TableColors
    tables: TablesLayout
    tree_colors: TreeColors
    scheduling: SchedulingBehavior

    @classmethod
    def from_config(cls, config: LayoutConfig) -> InstructionsTabParameters:
        general = config.general
        return cls(
            geometry=TabGeometry.from_config(config),
            baseline_viewport_height=general.responsive.baseline_viewport_height,
            max_stack_height=general.responsive.max_stack_height,
            base_graph_height=config.graphs.dimensions.height,
            right_column_width=config.tabs.instructions.right_column.width,
            right_column_height=config.tabs.instructions.right_column.height,
            instructions=config.tabs.instructions,
            graphs=config.graphs,
            pitch_stepper_style=PitchStepperStyle.from_general(general),
            table_colors=general.colors.tables,
            tables=general.tables,
            tree_colors=TreeColors.create(
                general.colors,
                accent=general.colors.headers.library,
            ),
            scheduling=config.behavior.scheduling,
        )
