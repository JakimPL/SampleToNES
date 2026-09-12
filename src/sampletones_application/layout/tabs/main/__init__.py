from pydantic import BaseModel

from sampletones_application.layout.tabs.main.advanced import AdvancedLayout
from sampletones_application.layout.tabs.main.config import ConfigLayout
from sampletones_application.layout.tabs.main.converter import ConverterLayout
from sampletones_application.layout.tabs.main.source import SourceSettingsLayout


class MainLayout(BaseModel, extra="forbid", frozen=True):
    config: ConfigLayout
    converter: ConverterLayout
    source: SourceSettingsLayout
    advanced: AdvancedLayout
