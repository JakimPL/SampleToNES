from __future__ import annotations

from dataclasses import dataclass

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.general.colors.feature import FeatureColors
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.general.plus_minus_buttons import PlusMinusButtonsLayout
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.parameters.geometry import TabGeometry
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.utils.palette.colors.base import BaseColor


@dataclass(frozen=True)
class SequencerTabParameters:
    """Everything the Sequencer tab coordinator needs, shaped for the coordinator.

    The right column stacks a module card, a samples card, and a history card; the history's
    expanded height and the collapsed header-bar height are flattened because the coordinator
    blends them into the samples card's reserved footprint. The tab's own ``SequencerLayout``
    is forwarded whole to its panels, alongside the cohesive general-layout blocks they draw
    with.
    """

    geometry: TabGeometry
    right_column_width: int
    right_column_height: int
    history_height: int
    header_bar_height: int
    sequencer: SequencerLayout
    inputs: InputsLayout
    plus_minus: PlusMinusButtonsLayout
    feature_colors: FeatureColors
    tree_colors: TreeColors
    muted_color: BaseColor
    scheduling: SchedulingBehavior

    @classmethod
    def from_config(cls, config: LayoutConfig) -> SequencerTabParameters:
        general = config.general
        return cls(
            geometry=TabGeometry.from_config(config),
            right_column_width=config.tabs.sequencer.right_column.width,
            right_column_height=config.tabs.sequencer.right_column.height,
            history_height=config.tabs.sequencer.history.height,
            header_bar_height=general.collapse.header_bar_height,
            sequencer=config.tabs.sequencer,
            inputs=general.inputs,
            plus_minus=general.plus_minus_buttons,
            feature_colors=general.colors.features,
            tree_colors=TreeColors.create(
                general.colors,
                accent=general.colors.headers.reconstruction,
            ),
            muted_color=general.colors.text.disabled,
            scheduling=config.behavior.scheduling,
        )
