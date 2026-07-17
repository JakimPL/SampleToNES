from pydantic import BaseModel


class PanelWithHeight(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int


class ConfigLayout(BaseModel, extra="forbid", frozen=True):
    height: int


class ReconstructorLayout(BaseModel, extra="forbid", frozen=True):
    drive_format: str


class ConverterLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    button_height: int


class AdvancedLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    button_height: int


class MainLayout(BaseModel, extra="forbid", frozen=True):
    config: ConfigLayout
    converter: ConverterLayout
    reconstructor: ReconstructorLayout
    advanced: AdvancedLayout
