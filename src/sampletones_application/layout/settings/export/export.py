from pydantic import BaseModel

from sampletones_application.layout.primitives import DialogGeometry
from sampletones_application.layout.settings.export.indicator import LoadingIndicatorLayout


class ExportSettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: DialogGeometry
    indicator: LoadingIndicatorLayout
