from pydantic import BaseModel

from sampletones_application.layout.general.colors.favorite import FavoriteColors
from sampletones_application.layout.general.colors.feature import FeatureColors
from sampletones_application.layout.general.colors.header import HeaderColors
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.general.colors.table import TableColors
from sampletones_application.layout.general.colors.text import TextColors


class GeneralColors(BaseModel, extra="forbid", frozen=True):
    text: TextColors
    favorites: FavoriteColors
    tables: TableColors
    paths: PathColors
    headers: HeaderColors
    features: FeatureColors
