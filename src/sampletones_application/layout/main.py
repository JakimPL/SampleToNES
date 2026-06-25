from pydantic import BaseModel


class PanelWithHeight(BaseModel, frozen=True):
    width: int
    height: int


class ExplorerLayout(BaseModel, frozen=True):
    width: int
    height: int


class ConfigLayout(BaseModel, frozen=True):
    height: int


class ReconstructorLayout(BaseModel, frozen=True):
    drive_format: str


class ConverterLayout(BaseModel, frozen=True):
    width: int
    height: int
    button_height: int


class AdvancedLayout(BaseModel, frozen=True):
    height: int


class MainLayout(BaseModel, frozen=True):
    explorer: ExplorerLayout
    config: ConfigLayout
    converter: ConverterLayout
    reconstructor: ReconstructorLayout
    advanced: AdvancedLayout
