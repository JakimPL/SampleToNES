from pydantic import BaseModel

from sampletones_application.utils.palette.color import PaletteColor


class TextColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    disabled: PaletteColor
    error: PaletteColor
    highlight: PaletteColor


class FavoriteColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    child: PaletteColor


class TableColors(BaseModel, extra="forbid", frozen=True):
    label: PaletteColor
    value: PaletteColor


class PathColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    hover: PaletteColor


class HeaderColors(BaseModel, extra="forbid", frozen=True):
    library: PaletteColor
    reconstruction: PaletteColor


class FeatureColors(BaseModel, extra="forbid", frozen=True):
    """The per-feature palette shared by every view that names a feature.

    The details tab's bar plots and the history panel's detail segments both
    paint from this block, so a feature keeps one colour across the
    application.
    """

    volume: PaletteColor
    arpeggio: PaletteColor
    pitch: PaletteColor
    duty_cycle: PaletteColor


class GeneralColors(BaseModel, extra="forbid", frozen=True):
    text: TextColors
    favorites: FavoriteColors
    tables: TableColors
    paths: PathColors
    headers: HeaderColors
    features: FeatureColors
