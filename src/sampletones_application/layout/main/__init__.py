from pydantic import BaseModel

from sampletones_application.layout.main.advanced import AdvancedLayout
from sampletones_application.layout.main.config import ConfigLayout
from sampletones_application.layout.main.converter import ConverterLayout
from sampletones_application.layout.main.reconstructor import ReconstructorLayout


class MainLayout(BaseModel, extra="forbid", frozen=True):
    config: ConfigLayout
    converter: ConverterLayout
    reconstructor: ReconstructorLayout
    advanced: AdvancedLayout
