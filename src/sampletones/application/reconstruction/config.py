from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sampletones.constants.enums import FeatureKey
from sampletones.typehints import Color

from ..constants import (
    COL_BAR_PLOT_ARPEGGIO,
    COL_BAR_PLOT_DUTY_CYCLE,
    COL_BAR_PLOT_PITCH,
    COL_BAR_PLOT_VOLUME,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_ARPEGGIO,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_DUTY_CYCLE,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_HI_PITCH,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_PITCH,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_VOLUME,
    VAL_BAR_PLOT_DUTY_CYCLE_Y_MAX,
    VAL_BAR_PLOT_DUTY_CYCLE_Y_MIN,
    VAL_BAR_PLOT_PITCH_Y_MAX,
    VAL_BAR_PLOT_PITCH_Y_MIN,
    VAL_BAR_PLOT_VOLUME_Y_MAX,
    VAL_BAR_PLOT_VOLUME_Y_MIN,
)


@dataclass(frozen=True)
class FeaturePlotConfig:
    feature_key: FeatureKey
    label: str
    color: Color
    y_min: float
    y_max: float
    y_ticks: Optional[Tuple[int, ...]]


FEATURE_PLOT_CONFIGS: Dict[FeatureKey, FeaturePlotConfig] = {
    FeatureKey.VOLUME: FeaturePlotConfig(
        feature_key=FeatureKey.VOLUME,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_VOLUME,
        color=COL_BAR_PLOT_VOLUME,
        y_min=VAL_BAR_PLOT_VOLUME_Y_MIN,
        y_max=VAL_BAR_PLOT_VOLUME_Y_MAX,
        y_ticks=(0, 4, 8, 12, 16),
    ),
    FeatureKey.ARPEGGIO: FeaturePlotConfig(
        feature_key=FeatureKey.ARPEGGIO,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_ARPEGGIO,
        color=COL_BAR_PLOT_ARPEGGIO,
        y_min=-1.0,
        y_max=-1.0,
        y_ticks=None,
    ),
    FeatureKey.PITCH: FeaturePlotConfig(
        feature_key=FeatureKey.PITCH,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_PITCH,
        color=COL_BAR_PLOT_PITCH,
        y_min=VAL_BAR_PLOT_PITCH_Y_MIN,
        y_max=VAL_BAR_PLOT_PITCH_Y_MAX,
        y_ticks=(-128, -96, -64, -32, 0, 32, 64, 96, 128),
    ),
    FeatureKey.HI_PITCH: FeaturePlotConfig(
        feature_key=FeatureKey.HI_PITCH,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_HI_PITCH,
        color=COL_BAR_PLOT_PITCH,
        y_min=VAL_BAR_PLOT_PITCH_Y_MIN,
        y_max=VAL_BAR_PLOT_PITCH_Y_MAX,
        y_ticks=(-128, -96, -64, -32, 0, 32, 64, 96, 128),
    ),
    FeatureKey.DUTY_CYCLE: FeaturePlotConfig(
        feature_key=FeatureKey.DUTY_CYCLE,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_DUTY_CYCLE,
        color=COL_BAR_PLOT_DUTY_CYCLE,
        y_min=VAL_BAR_PLOT_DUTY_CYCLE_Y_MIN,
        y_max=VAL_BAR_PLOT_DUTY_CYCLE_Y_MAX,
        y_ticks=(0, 1, 2, 3),
    ),
}

FEATURE_DISPLAY_ORDER: List[FeatureKey] = [
    FeatureKey.VOLUME,
    FeatureKey.ARPEGGIO,
    FeatureKey.PITCH,
    FeatureKey.HI_PITCH,
    FeatureKey.DUTY_CYCLE,
]
