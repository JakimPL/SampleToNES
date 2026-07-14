from pydantic import BaseModel

from sampletones_application.utils.palette import PaletteColor


class TextColors(BaseModel, extra="forbid", frozen=True):
    white: PaletteColor
    default: PaletteColor
    disabled: PaletteColor
    error: PaletteColor
    highlight: PaletteColor
    traceback: PaletteColor


class FileColors(BaseModel, extra="forbid", frozen=True):
    wave: PaletteColor
    library: PaletteColor
    reconstruction: PaletteColor
    directory_not_expanded: PaletteColor


class FavoriteColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    child: PaletteColor


class ButtonColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    active: PaletteColor
    hovered: PaletteColor
    light: PaletteColor


class BackgroundColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    dark: PaletteColor
    light: PaletteColor
    menu: PaletteColor
    input_invalid: PaletteColor


class TableColors(BaseModel, extra="forbid", frozen=True):
    header: PaletteColor
    row: PaletteColor
    row_alternative: PaletteColor
    border: PaletteColor
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
    files: FileColors
    favorites: FavoriteColors
    buttons: ButtonColors
    backgrounds: BackgroundColors
    tables: TableColors
    paths: PathColors
    headers: HeaderColors
    features: FeatureColors
