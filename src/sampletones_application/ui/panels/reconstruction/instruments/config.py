from dataclasses import dataclass
from typing import Dict, Final, Optional, Tuple

from sampletones_application.categories.elements.reconstructions import (
    ReconstructionsInstrumentsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general import FeatureColors
from sampletones_core.constants.enums import FeatureKey, LibraryGeneratorName
from sampletones_core.features import feature_range, supported_features
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


FEATURE_TICK_STEPS: Final[Dict[FeatureKey, int]] = {
    FeatureKey.VOLUME: 4,
    FeatureKey.ARPEGGIO: 32,
    FeatureKey.PITCH: 32,
    FeatureKey.HI_PITCH: 32,
    FeatureKey.DUTY_CYCLE: 1,
}


def make_feature_plot_configs(
    feature_colors: FeatureColors,
    language_manager: LanguageManager,
) -> Dict[LibraryGeneratorName, Dict[FeatureKey, FeaturePlotConfig]]:
    labels = _feature_labels(language_manager)
    colors = _feature_colors(feature_colors)
    return _build_plot_configs(labels, colors)


def _feature_labels(language_manager: LanguageManager) -> Dict[FeatureKey, str]:
    lbl_volume = language_manager[
        Page.RECONSTRUCTIONS,
        Panel.INSTRUMENTS,
        TextType.LABEL,
        ReconstructionsInstrumentsElements.VOLUME_LABEL,
    ]
    lbl_arpeggio = language_manager[
        Page.RECONSTRUCTIONS,
        Panel.INSTRUMENTS,
        TextType.LABEL,
        ReconstructionsInstrumentsElements.ARPEGGIO_LABEL,
    ]
    lbl_pitch = language_manager[
        Page.RECONSTRUCTIONS,
        Panel.INSTRUMENTS,
        TextType.LABEL,
        ReconstructionsInstrumentsElements.PITCH_LABEL,
    ]
    lbl_hi_pitch = language_manager[
        Page.RECONSTRUCTIONS,
        Panel.INSTRUMENTS,
        TextType.LABEL,
        ReconstructionsInstrumentsElements.HI_PITCH_LABEL,
    ]
    lbl_duty_cycle = language_manager[
        Page.RECONSTRUCTIONS,
        Panel.INSTRUMENTS,
        TextType.LABEL,
        ReconstructionsInstrumentsElements.DUTY_CYCLE_LABEL,
    ]

    return {
        FeatureKey.VOLUME: lbl_volume,
        FeatureKey.ARPEGGIO: lbl_arpeggio,
        FeatureKey.PITCH: lbl_pitch,
        FeatureKey.HI_PITCH: lbl_hi_pitch,
        FeatureKey.DUTY_CYCLE: lbl_duty_cycle,
    }


def _feature_colors(feature_colors: FeatureColors) -> Dict[FeatureKey, Color]:
    return {
        FeatureKey.VOLUME: feature_colors.volume,
        FeatureKey.ARPEGGIO: feature_colors.arpeggio,
        FeatureKey.PITCH: feature_colors.pitch,
        FeatureKey.HI_PITCH: feature_colors.pitch,
        FeatureKey.DUTY_CYCLE: feature_colors.duty_cycle,
    }


def _build_plot_configs(
    labels: Dict[FeatureKey, str],
    colors: Dict[FeatureKey, Color],
) -> Dict[LibraryGeneratorName, Dict[FeatureKey, FeaturePlotConfig]]:
    configs: Dict[LibraryGeneratorName, Dict[FeatureKey, FeaturePlotConfig]] = {}
    for kind in LibraryGeneratorName:
        configs[kind] = _build_kind_plot_configs(kind, labels, colors)

    return configs


def _build_kind_plot_configs(
    kind: LibraryGeneratorName,
    labels: Dict[FeatureKey, str],
    colors: Dict[FeatureKey, Color],
) -> Dict[FeatureKey, FeaturePlotConfig]:
    kind_configs: Dict[FeatureKey, FeaturePlotConfig] = {}
    for feature_key in supported_features(kind):
        kind_configs[feature_key] = _build_plot_config(kind, feature_key, labels, colors)
    return kind_configs


def _build_plot_config(
    kind: LibraryGeneratorName,
    feature_key: FeatureKey,
    labels: Dict[FeatureKey, str],
    colors: Dict[FeatureKey, Color],
) -> FeaturePlotConfig:
    data = feature_range(kind, feature_key)
    return FeaturePlotConfig(
        feature_key=feature_key,
        label=labels[feature_key],
        color=colors[feature_key],
        y_min=float(data.minimum),
        y_max=float(data.maximum),
        y_ticks=_make_ticks(data.minimum, data.maximum, FEATURE_TICK_STEPS[feature_key]),
        data_range=(data.minimum, data.maximum),
    )


def _make_ticks(minimum: int, maximum: int, tick_step: int) -> Tuple[int, ...]:
    step = 1 if (maximum - minimum) < tick_step else tick_step
    return tuple(range(minimum, maximum + 1, step))
