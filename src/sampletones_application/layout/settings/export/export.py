from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions
from sampletones_application.layout.settings.export.indicator import LoadingIndicatorLayout


class ExportSettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: Dimensions
    indicator: LoadingIndicatorLayout
