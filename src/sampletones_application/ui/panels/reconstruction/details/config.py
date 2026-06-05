from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sampletones_application.categories.elements.reconstructions import (
    ReconstructionsDetailsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.reconstructions import ReconstructionsLayout
from sampletones_core.constants.enums import FeatureKey
from sampletones_shared.types.application import Color


@dataclass(frozen=True)
class FeaturePlotConfig:
    feature_key: FeatureKey
    label: str
    color: Color
    y_min: float
    y_max: float
    y_ticks: Optional[Tuple[int, ...]]
    data_range: Tuple[int, int]


def make_feature_plot_configs(
    layout: ReconstructionsLayout,
    language_manager: LanguageManager,
) -> Dict[FeatureKey, FeaturePlotConfig]:
    lbl_volume = language_manager[
        TextKey(
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            ReconstructionsDetailsElements.VOLUME_LABEL,
        )
    ]
    lbl_arpeggio = language_manager[
        TextKey(
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            ReconstructionsDetailsElements.ARPEGGIO_LABEL,
        )
    ]
    lbl_pitch = language_manager[
        TextKey(
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            ReconstructionsDetailsElements.PITCH_LABEL,
        )
    ]
    lbl_hi_pitch = language_manager[
        TextKey(
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            ReconstructionsDetailsElements.HI_PITCH_LABEL,
        )
    ]
    lbl_duty_cycle = language_manager[
        TextKey(
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            ReconstructionsDetailsElements.DUTY_CYCLE_LABEL,
        )
    ]

    return {
        FeatureKey.VOLUME: FeaturePlotConfig(
            feature_key=FeatureKey.VOLUME,
            label=lbl_volume,
            color=layout.colors.volume,
            y_min=layout.bar_plots.volume.min_y,
            y_max=layout.bar_plots.volume.max_y,
            y_ticks=(0, 4, 8, 12, 16),
            data_range=(0, 15),
        ),
        FeatureKey.ARPEGGIO: FeaturePlotConfig(
            feature_key=FeatureKey.ARPEGGIO,
            label=lbl_arpeggio,
            color=layout.colors.arpeggio,
            y_min=layout.bar_plots.arpeggio.min_y,
            y_max=layout.bar_plots.arpeggio.max_y,
            y_ticks=(-128, -96, -64, -32, 0, 32, 64, 96, 128),
            data_range=(-128, 127),
        ),
        FeatureKey.PITCH: FeaturePlotConfig(
            feature_key=FeatureKey.PITCH,
            label=lbl_pitch,
            color=layout.colors.pitch,
            y_min=layout.bar_plots.pitch.min_y,
            y_max=layout.bar_plots.pitch.max_y,
            y_ticks=(-128, -96, -64, -32, 0, 32, 64, 96, 128),
            data_range=(-128, 127),
        ),
        FeatureKey.HI_PITCH: FeaturePlotConfig(
            feature_key=FeatureKey.HI_PITCH,
            label=lbl_hi_pitch,
            color=layout.colors.pitch,
            y_min=layout.bar_plots.pitch.min_y,
            y_max=layout.bar_plots.pitch.max_y,
            y_ticks=(-128, -96, -64, -32, 0, 32, 64, 96, 128),
            data_range=(-128, 127),
        ),
        FeatureKey.DUTY_CYCLE: FeaturePlotConfig(
            feature_key=FeatureKey.DUTY_CYCLE,
            label=lbl_duty_cycle,
            color=layout.colors.duty_cycle,
            y_min=layout.bar_plots.duty_cycle.min_y,
            y_max=layout.bar_plots.duty_cycle.max_y,
            y_ticks=(0, 1, 2, 3),
            data_range=(0, 3),
        ),
    }


FEATURE_DISPLAY_ORDER: List[FeatureKey] = [
    FeatureKey.VOLUME,
    FeatureKey.ARPEGGIO,
    # FeatureKey.PITCH,
    # FeatureKey.HI_PITCH,
    FeatureKey.DUTY_CYCLE,
]
