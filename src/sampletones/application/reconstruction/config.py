from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sampletones.constants.enums import FeatureKey
from sampletones_shared.types.application import Color

from ..constants.reconstructions import (
    COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_ARPEGGIO,
    COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_DUTY_CYCLE,
    COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_PITCH,
    COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_VOLUME,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_ARPEGGIO,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_DUTY_CYCLE,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_HI_PITCH,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_PITCH,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_VOLUME,
    VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_ARPEGGIO_Y,
    VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_DUTY_CYCLE_Y,
    VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_PITCH_Y,
    VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_VOLUME_Y,
    VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_ARPEGGIO_Y,
    VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_DUTY_CYCLE_Y,
    VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_PITCH_Y,
    VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_VOLUME_Y,
)


@dataclass(frozen=True)
class FeaturePlotConfig:
    feature_key: FeatureKey
    label: str
    color: Color
    y_min: float
    y_max: float
    y_ticks: Optional[Tuple[int, ...]]
    data_range: Tuple[int, int]


FEATURE_PLOT_CONFIGS: Dict[FeatureKey, FeaturePlotConfig] = {
    FeatureKey.VOLUME: FeaturePlotConfig(
        feature_key=FeatureKey.VOLUME,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_VOLUME,
        color=COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_VOLUME,
        y_min=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_VOLUME_Y,
        y_max=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_VOLUME_Y,
        y_ticks=(0, 4, 8, 12, 16),
        data_range=(0, 15),
    ),
    FeatureKey.ARPEGGIO: FeaturePlotConfig(
        feature_key=FeatureKey.ARPEGGIO,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_ARPEGGIO,
        color=COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_ARPEGGIO,
        y_min=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_ARPEGGIO_Y,
        y_max=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_ARPEGGIO_Y,
        y_ticks=(-128, -96, -64, -32, 0, 32, 64, 96, 128),
        data_range=(-128, 127),
    ),
    FeatureKey.PITCH: FeaturePlotConfig(
        feature_key=FeatureKey.PITCH,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_PITCH,
        color=COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_PITCH,
        y_min=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_PITCH_Y,
        y_max=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_PITCH_Y,
        y_ticks=(-128, -96, -64, -32, 0, 32, 64, 96, 128),
        data_range=(-128, 127),
    ),
    FeatureKey.HI_PITCH: FeaturePlotConfig(
        feature_key=FeatureKey.HI_PITCH,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_HI_PITCH,
        color=COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_PITCH,
        y_min=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_PITCH_Y,
        y_max=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_PITCH_Y,
        y_ticks=(-128, -96, -64, -32, 0, 32, 64, 96, 128),
        data_range=(-128, 127),
    ),
    FeatureKey.DUTY_CYCLE: FeaturePlotConfig(
        feature_key=FeatureKey.DUTY_CYCLE,
        label=LBL_PLOT_LABEL_RECONSTRUCTIONS_DETAILS_DUTY_CYCLE,
        color=COL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_DUTY_CYCLE,
        y_min=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MIN_DUTY_CYCLE_Y,
        y_max=VAL_BAR_PLOT_RECONSTRUCTIONS_DETAILS_MAX_DUTY_CYCLE_Y,
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
